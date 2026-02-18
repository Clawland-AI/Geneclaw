"""Benchmarks — measure evolution pipeline performance (GEP v0 / M5).

Provides synthetic workload generation and timing for each pipeline stage:
diagnosis, proposal generation, gatekeeper validation, and apply (dry-run).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from geneclaw.evolver import diagnose_events
from geneclaw.gatekeeper import validate_proposal
from geneclaw.models import EvolutionProposal, RunEvent
from geneclaw.recorder import RunRecorder


@dataclass
class StageTiming:
    """Timing result for a single pipeline stage."""

    stage: str = ""
    duration_ms: float = 0.0
    iterations: int = 1
    avg_ms: float = 0.0


@dataclass
class BenchmarkResult:
    """Aggregate benchmark results."""

    event_count: int = 0
    stages: list[StageTiming] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": self.event_count,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "stages": [
                {
                    "stage": s.stage,
                    "duration_ms": round(s.duration_ms, 2),
                    "iterations": s.iterations,
                    "avg_ms": round(s.avg_ms, 2),
                }
                for s in self.stages
            ],
        }


def _generate_synthetic_events(count: int) -> list[dict[str, Any]]:
    """Create a batch of synthetic run events for benchmarking."""
    events: list[dict[str, Any]] = []
    tools = ["exec_command", "read_file", "write_file", "web_search", "code_analysis"]

    for i in range(count):
        ts = datetime.now(timezone.utc).isoformat()
        if i % 5 == 0:
            events.append({
                "timestamp": ts,
                "session_key": "bench",
                "event_type": "inbound_msg",
                "preview": f"Benchmark message {i}",
            })
        elif i % 5 == 4:
            events.append({
                "timestamp": ts,
                "session_key": "bench",
                "event_type": "outbound_msg",
                "preview": f"Response {i}",
            })
        elif i % 7 == 0:
            events.append({
                "timestamp": ts,
                "session_key": "bench",
                "event_type": "exception",
                "error": f"SyntheticError: failure #{i}",
                "success": False,
            })
        else:
            tool = tools[i % len(tools)]
            success = i % 3 != 0
            events.append({
                "timestamp": ts,
                "session_key": "bench",
                "event_type": "tool_end",
                "tool_name": tool,
                "duration_ms": float(i * 10),
                "success": success,
                "error": None if success else f"ToolError: {tool} failed",
            })

    return events


def _make_synthetic_proposal(files: int = 3, diff_lines: int = 20) -> EvolutionProposal:
    """Create a synthetic proposal for gatekeeper benchmarking."""
    touched = [f"geneclaw/synth_{i}.py" for i in range(files)]
    diff_parts = ["--- a/geneclaw/synth_0.py", "+++ b/geneclaw/synth_0.py", "@@ -1,3 +1,5 @@"]
    for j in range(diff_lines - 3):
        diff_parts.append(f"+# synthetic line {j}")

    return EvolutionProposal(
        id=str(uuid.uuid4()),
        title="benchmark-synthetic",
        objective="Synthetic proposal for benchmarking",
        risk_level="low",
        files_touched=touched,
        unified_diff="\n".join(diff_parts),
        tests_to_run=["pytest tests/"],
        rollback_plan="git checkout -",
    )


def run_benchmarks(
    *,
    event_counts: list[int] | None = None,
    gate_iterations: int = 100,
    allowlist_paths: list[str] | None = None,
    denylist_paths: list[str] | None = None,
    max_patch_lines: int = 500,
) -> BenchmarkResult:
    """Run pipeline benchmarks with synthetic data.

    Parameters
    ----------
    event_counts:
        List of event counts to benchmark diagnosis against.
        Defaults to [100, 500, 1000].
    gate_iterations:
        Number of gatekeeper validation iterations.
    allowlist_paths / denylist_paths / max_patch_lines:
        Gatekeeper constraints.
    """
    if event_counts is None:
        event_counts = [100, 500, 1000]

    result = BenchmarkResult()
    total_start = time.monotonic()

    # Stage 1: Diagnosis at various event counts
    for count in event_counts:
        events = _generate_synthetic_events(count)
        result.event_count = max(result.event_count, count)

        start = time.monotonic()
        iterations = 10
        for _ in range(iterations):
            diagnose_events(events)
        elapsed = (time.monotonic() - start) * 1000

        result.stages.append(StageTiming(
            stage=f"diagnose({count} events)",
            duration_ms=elapsed,
            iterations=iterations,
            avg_ms=elapsed / iterations,
        ))

    # Stage 2: Gatekeeper validation
    proposal = _make_synthetic_proposal()
    allow = allowlist_paths or ["geneclaw/", "nanobot/", "tests/", "docs/"]
    deny = denylist_paths or [".env", "secrets/", ".git/"]

    start = time.monotonic()
    for _ in range(gate_iterations):
        validate_proposal(
            proposal,
            allowlist_paths=allow,
            denylist_paths=deny,
            max_patch_lines=max_patch_lines,
        )
    elapsed = (time.monotonic() - start) * 1000

    result.stages.append(StageTiming(
        stage="gatekeeper_validate",
        duration_ms=elapsed,
        iterations=gate_iterations,
        avg_ms=elapsed / gate_iterations,
    ))

    # Stage 3: Gatekeeper with large diff
    large_proposal = _make_synthetic_proposal(files=10, diff_lines=400)
    start = time.monotonic()
    for _ in range(gate_iterations):
        validate_proposal(
            large_proposal,
            allowlist_paths=allow,
            denylist_paths=deny,
            max_patch_lines=max_patch_lines,
        )
    elapsed = (time.monotonic() - start) * 1000

    result.stages.append(StageTiming(
        stage="gatekeeper_validate(large_diff)",
        duration_ms=elapsed,
        iterations=gate_iterations,
        avg_ms=elapsed / gate_iterations,
    ))

    # Stage 4: Event store write + read benchmark
    from geneclaw.event_store import EventStore
    from geneclaw.models import EvoEvent
    import tempfile

    tmp_ws = Path(tempfile.mkdtemp())
    store = EventStore(tmp_ws, redact=True)
    write_count = 200

    start = time.monotonic()
    for i in range(write_count):
        store.record(EvoEvent(
            event_type="evolve_generated",
            proposal_id=f"bench-{i}",
            risk_level="low",
        ))
    write_elapsed = (time.monotonic() - start) * 1000

    result.stages.append(StageTiming(
        stage=f"event_store_write({write_count})",
        duration_ms=write_elapsed,
        iterations=write_count,
        avg_ms=write_elapsed / write_count,
    ))

    start = time.monotonic()
    read_iters = 50
    for _ in range(read_iters):
        store.iter_events()
    read_elapsed = (time.monotonic() - start) * 1000

    result.stages.append(StageTiming(
        stage=f"event_store_read({write_count} events)",
        duration_ms=read_elapsed,
        iterations=read_iters,
        avg_ms=read_elapsed / read_iters,
    ))

    # Cleanup temp dir
    import shutil
    shutil.rmtree(tmp_ws, ignore_errors=True)

    result.total_duration_ms = (time.monotonic() - total_start) * 1000
    return result
