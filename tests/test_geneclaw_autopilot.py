"""Tests for geneclaw autopilot and benchmarks (M5)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from geneclaw.autopilot import (
    AutopilotConfig,
    AutopilotResult,
    CycleResult,
    run_autopilot,
    _risk_allowed,
)
from geneclaw.benchmarks import (
    BenchmarkResult,
    StageTiming,
    run_benchmarks,
    _generate_synthetic_events,
    _make_synthetic_proposal,
)
from geneclaw.models import EvoEvent
from geneclaw.event_store import EventStore
from geneclaw.recorder import RunRecorder


# ---------------------------------------------------------------------------
# Autopilot — risk check
# ---------------------------------------------------------------------------


def test_risk_allowed_low():
    assert _risk_allowed("low", "low") is True


def test_risk_allowed_medium_blocked():
    assert _risk_allowed("medium", "low") is False


def test_risk_allowed_none_blocks_all():
    assert _risk_allowed("low", "none") is False
    assert _risk_allowed("medium", "none") is False
    assert _risk_allowed("high", "none") is False


# ---------------------------------------------------------------------------
# Autopilot — dry-run cycle
# ---------------------------------------------------------------------------


def test_autopilot_dry_run_no_events(tmp_path: Path) -> None:
    """Autopilot with no events should produce skipped cycles."""
    config = AutopilotConfig(max_cycles=2, cooldown_seconds=0, dry_run=True)
    result = asyncio.run(run_autopilot(
        workspace=tmp_path,
        provider=None,
        model="test/model",
        config=config,
    ))
    assert result.cycles_run == 2
    assert result.cycles_skipped == 2
    assert result.proposals_generated == 0


def test_autopilot_dry_run_with_events(tmp_path: Path) -> None:
    """Autopilot with events should generate proposals in dry-run."""
    rec = RunRecorder(tmp_path, "test-session", max_chars=500, redact=False)
    rec.record_inbound("cli", "test-session", "hello")
    t = rec.record_tool_start("web_search")
    rec.record_tool_end("web_search", t, success=False, error="TimeoutError")
    rec.record_exception("TimeoutError")

    config = AutopilotConfig(max_cycles=2, cooldown_seconds=0, dry_run=True)
    result = asyncio.run(run_autopilot(
        workspace=tmp_path,
        provider=None,
        model="test/model",
        config=config,
    ))
    assert result.proposals_generated == 2
    assert result.proposals_applied == 0
    for cr in result.cycle_results:
        assert not cr.applied
        assert cr.apply_result == "dry-run"


def test_autopilot_result_to_dict(tmp_path: Path) -> None:
    """AutopilotResult.to_dict() should be JSON-serializable."""
    config = AutopilotConfig(max_cycles=1, cooldown_seconds=0, dry_run=True)
    result = asyncio.run(run_autopilot(
        workspace=tmp_path,
        provider=None,
        model="test/model",
        config=config,
    ))
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "cycles_run" in d
    serialized = json.dumps(d)
    assert json.loads(serialized)


def test_autopilot_records_events(tmp_path: Path) -> None:
    """Autopilot should record evolve_generated events."""
    rec = RunRecorder(tmp_path, "ap-test", max_chars=500, redact=False)
    rec.record_inbound("cli", "ap-test", "test message")
    t = rec.record_tool_start("exec_command")
    rec.record_tool_end("exec_command", t, success=False, error="Error")
    rec.record_exception("Error")

    config = AutopilotConfig(max_cycles=1, cooldown_seconds=0, dry_run=True)
    asyncio.run(run_autopilot(
        workspace=tmp_path,
        provider=None,
        model="test/model",
        config=config,
    ))

    store = EventStore(tmp_path, redact=False)
    events = store.iter_events()
    assert any(e["event_type"] == "evolve_generated" for e in events)


# ---------------------------------------------------------------------------
# Benchmarks — synthetic data
# ---------------------------------------------------------------------------


def test_generate_synthetic_events():
    events = _generate_synthetic_events(100)
    assert len(events) == 100
    types = {e["event_type"] for e in events}
    assert "inbound_msg" in types or "tool_end" in types


def test_make_synthetic_proposal():
    proposal = _make_synthetic_proposal(files=3, diff_lines=20)
    assert len(proposal.files_touched) == 3
    assert len(proposal.unified_diff.splitlines()) >= 20
    assert proposal.title == "benchmark-synthetic"


def test_run_benchmarks():
    result = run_benchmarks(event_counts=[50, 100], gate_iterations=10)
    assert result.total_duration_ms > 0
    assert len(result.stages) >= 4
    for s in result.stages:
        assert s.iterations > 0
        assert s.avg_ms >= 0


def test_benchmark_result_to_dict():
    result = run_benchmarks(event_counts=[50], gate_iterations=5)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "stages" in d
    assert "total_duration_ms" in d
    serialized = json.dumps(d)
    assert json.loads(serialized)


def test_benchmark_event_store_stages():
    """Benchmark should include event_store write and read stages."""
    result = run_benchmarks(event_counts=[50], gate_iterations=5)
    stage_names = [s.stage for s in result.stages]
    assert any("event_store_write" in n for n in stage_names)
    assert any("event_store_read" in n for n in stage_names)
