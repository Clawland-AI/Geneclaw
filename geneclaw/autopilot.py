"""Autopilot — automated evolution loop controller (GEP v0 / M5).

Orchestrates: observe → diagnose → evolve → gate → (optional) apply → record
in configurable cycles with safety constraints.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from geneclaw.event_store import EventStore
from geneclaw.evolver import diagnose_events, generate_proposal
from geneclaw.gatekeeper import validate_proposal
from geneclaw.models import EvoEvent, EvolutionProposal
from geneclaw.recorder import RunRecorder
from geneclaw.report import generate_report


@dataclass
class AutopilotConfig:
    """Configuration for an autopilot run."""

    max_cycles: int = 3
    cooldown_seconds: float = 5.0
    auto_approve_risk: Literal["low", "none"] = "low"
    since_hours: float = 24.0
    max_events: int = 500
    dry_run: bool = True
    stop_on_failure: bool = True


@dataclass
class CycleResult:
    """Outcome of a single autopilot cycle."""

    cycle: int = 0
    proposal_id: str = ""
    proposal_title: str = ""
    risk_level: str = "low"
    diagnosis_summary: str = ""
    gate_passed: bool = False
    gate_reasons: list[str] = field(default_factory=list)
    applied: bool = False
    apply_result: str = ""
    duration_ms: float = 0.0
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class AutopilotResult:
    """Aggregate outcome of an autopilot run."""

    cycles_run: int = 0
    cycles_skipped: int = 0
    proposals_generated: int = 0
    proposals_gated: int = 0
    proposals_applied: int = 0
    proposals_failed: int = 0
    cycle_results: list[CycleResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycles_run": self.cycles_run,
            "cycles_skipped": self.cycles_skipped,
            "proposals_generated": self.proposals_generated,
            "proposals_gated": self.proposals_gated,
            "proposals_applied": self.proposals_applied,
            "proposals_failed": self.proposals_failed,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "cycle_results": [
                {
                    "cycle": cr.cycle,
                    "proposal_id": cr.proposal_id,
                    "proposal_title": cr.proposal_title,
                    "risk_level": cr.risk_level,
                    "diagnosis_summary": cr.diagnosis_summary,
                    "gate_passed": cr.gate_passed,
                    "gate_reasons": cr.gate_reasons,
                    "applied": cr.applied,
                    "apply_result": cr.apply_result,
                    "duration_ms": round(cr.duration_ms, 2),
                    "skipped": cr.skipped,
                    "skip_reason": cr.skip_reason,
                }
                for cr in self.cycle_results
            ],
        }


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "none": -1}


def _risk_allowed(proposal_risk: str, threshold: str) -> bool:
    """Return True if the proposal risk is at or below the auto-approve threshold."""
    if threshold == "none":
        return False
    return _RISK_ORDER.get(proposal_risk, 99) <= _RISK_ORDER.get(threshold, -1)


async def run_autopilot(
    workspace: Path,
    provider: Any | None,
    model: str,
    config: AutopilotConfig,
    *,
    allowlist_paths: list[str] | None = None,
    denylist_paths: list[str] | None = None,
    max_patch_lines: int = 500,
    redact: bool = True,
) -> AutopilotResult:
    """Execute the autopilot evolution loop.

    Parameters
    ----------
    workspace:
        Nanobot workspace path.
    provider:
        LLM provider instance (None = heuristic-only mode).
    model:
        Model identifier string.
    config:
        Autopilot configuration.
    allowlist_paths / denylist_paths / max_patch_lines:
        Gatekeeper constraints.
    redact:
        Whether to redact secrets in event logs.
    """
    store = EventStore(workspace, redact=redact)
    result = AutopilotResult()
    run_start = time.monotonic()

    for cycle_num in range(1, config.max_cycles + 1):
        cycle_start = time.monotonic()
        cr = CycleResult(cycle=cycle_num)

        try:
            # 1. Collect events
            all_events: list[dict[str, Any]] = []
            for sk in RunRecorder.list_sessions(workspace):
                rec = RunRecorder(workspace=workspace, session_key=sk, redact=True)
                all_events.extend(rec.iter_events(max_events=config.max_events))

            diagnosis = diagnose_events(all_events)
            cr.diagnosis_summary = diagnosis.get("summary", "")

            if diagnosis["failure_count"] == 0 and not all_events:
                cr.skipped = True
                cr.skip_reason = "No events or failures to diagnose"
                cr.duration_ms = (time.monotonic() - cycle_start) * 1000
                result.cycle_results.append(cr)
                result.cycles_skipped += 1
                result.cycles_run += 1
                continue

            # 2. Generate proposal
            if provider is not None:
                proposal = await generate_proposal(
                    workspace=workspace,
                    provider=provider,
                    model=model,
                    since_hours=config.since_hours,
                    max_events=config.max_events,
                )
            else:
                proposal = EvolutionProposal(
                    id=str(uuid.uuid4()),
                    title="heuristic-only",
                    objective=f"Heuristic diagnosis: {diagnosis['summary']}",
                    evidence=[diagnosis["summary"]],
                    risk_level="low",
                )

            result.proposals_generated += 1
            cr.proposal_id = proposal.id
            cr.proposal_title = proposal.title
            cr.risk_level = proposal.risk_level

            # Record evolve event
            store.record(EvoEvent(
                event_type="evolve_generated",
                proposal_id=proposal.id,
                risk_level=proposal.risk_level,
                files_touched=proposal.files_touched,
                diff_lines=len(proposal.unified_diff.splitlines()) if proposal.unified_diff else 0,
                result="ok",
            ))

            # 3. Gatekeeper validation
            if proposal.unified_diff.strip():
                ok, reasons = validate_proposal(
                    proposal,
                    allowlist_paths=allowlist_paths,
                    denylist_paths=denylist_paths,
                    max_patch_lines=max_patch_lines,
                )
                cr.gate_passed = ok
                cr.gate_reasons = reasons
                if not ok:
                    result.proposals_gated += 1
            else:
                cr.gate_passed = True
                cr.gate_reasons = []

            # 4. Decide whether to apply
            should_apply = (
                not config.dry_run
                and cr.gate_passed
                and proposal.unified_diff.strip()
                and _risk_allowed(proposal.risk_level, config.auto_approve_risk)
            )

            if should_apply:
                from geneclaw.apply import apply_unified_diff

                store.record(EvoEvent(
                    event_type="apply_attempted",
                    proposal_id=proposal.id,
                    risk_level=proposal.risk_level,
                    files_touched=proposal.files_touched,
                ))

                success, msg = apply_unified_diff(
                    proposal,
                    repo_root=workspace,
                    allowlist_paths=allowlist_paths,
                    denylist_paths=denylist_paths,
                    max_patch_lines=max_patch_lines,
                    dry_run=False,
                )
                cr.applied = True
                cr.apply_result = msg[:500]

                store.record(EvoEvent(
                    event_type="apply_succeeded" if success else "apply_failed",
                    proposal_id=proposal.id,
                    risk_level=proposal.risk_level,
                    files_touched=proposal.files_touched,
                    result=f"{'ok' if success else 'fail'}: {msg[:200]}",
                ))

                if success:
                    result.proposals_applied += 1
                else:
                    result.proposals_failed += 1
                    if config.stop_on_failure:
                        cr.duration_ms = (time.monotonic() - cycle_start) * 1000
                        result.cycle_results.append(cr)
                        result.cycles_run += 1
                        break
            else:
                cr.applied = False
                cr.apply_result = (
                    "dry-run" if config.dry_run
                    else "risk too high for auto-approve" if not _risk_allowed(proposal.risk_level, config.auto_approve_risk)
                    else "no diff" if not proposal.unified_diff.strip()
                    else "gatekeeper rejected"
                )

        except Exception as exc:
            logger.warning(f"Autopilot cycle {cycle_num} error: {exc}")
            cr.skipped = True
            cr.skip_reason = f"Error: {str(exc)[:200]}"
            result.cycles_skipped += 1

        cr.duration_ms = (time.monotonic() - cycle_start) * 1000
        result.cycle_results.append(cr)
        result.cycles_run += 1

        if cycle_num < config.max_cycles and config.cooldown_seconds > 0:
            await asyncio.sleep(config.cooldown_seconds)

    result.total_duration_ms = (time.monotonic() - run_start) * 1000
    return result
