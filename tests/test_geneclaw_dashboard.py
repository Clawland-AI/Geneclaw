"""Tests for geneclaw.dashboard.loader — data loading, redaction, edge cases."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from geneclaw.dashboard.loader import (
    _parse_jsonl,
    _redact_value,
    flatten_stages,
    load_benchmarks,
    load_events,
    redact_dataframe,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_evo_event(
    event_type: str = "evolve_generated",
    risk: str = "low",
    proposal_id: str = "p-1",
    title: str = "test proposal",
    result: str = "ok",
    ts: str | None = None,
) -> dict:
    return {
        "event_id": f"eid-{proposal_id}",
        "timestamp": ts or datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "session_key": "sess-1",
        "proposal_id": proposal_id,
        "risk_level": risk,
        "files_touched": ["geneclaw/foo.py"],
        "diff_lines": 5,
        "tests_to_run": ["pytest tests/"],
        "parent_event_id": "",
        "result": result,
        "title": title,
        "objective": "improve reliability",
        "rollback_plan": "git revert HEAD",
    }


def _make_bench_result(event_count: int = 100, total_ms: float = 42.0) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_count": event_count,
        "total_duration_ms": total_ms,
        "stages": [
            {"stage": "diagnosis", "duration_ms": 10.0, "iterations": 1, "avg_ms": 10.0},
            {"stage": "gatekeeper", "duration_ms": 20.0, "iterations": 100, "avg_ms": 0.2},
        ],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# Tests: _parse_jsonl
# ---------------------------------------------------------------------------


def test_parse_jsonl_missing_file(tmp_path: Path) -> None:
    assert _parse_jsonl(tmp_path / "nope.jsonl") == []


def test_parse_jsonl_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert _parse_jsonl(p) == []


def test_parse_jsonl_skips_bad_lines(tmp_path: Path) -> None:
    p = tmp_path / "mixed.jsonl"
    p.write_text('{"a":1}\nNOT_JSON\n{"b":2}\n', encoding="utf-8")
    rows = _parse_jsonl(p)
    assert len(rows) == 2
    assert rows[0]["a"] == 1
    assert rows[1]["b"] == 2


# ---------------------------------------------------------------------------
# Tests: redaction
# ---------------------------------------------------------------------------


def test_redact_value_masks_api_key() -> None:
    text = 'Authorization: Bearer sk-abcdefghij1234567890abcdef'
    result = _redact_value(text)
    assert "sk-abcdef" not in result
    assert "***REDACTED***" in result


def test_redact_value_passthrough_safe() -> None:
    assert _redact_value("hello world") == "hello world"
    assert _redact_value(42) == 42
    assert _redact_value(None) is None


def test_redact_dataframe(tmp_path: Path) -> None:
    import pandas as pd

    df = pd.DataFrame({
        "safe": ["hello", "world"],
        "secret": ["api_key=sk-supersecretkey123456", "ok"],
    })
    result = redact_dataframe(df)
    assert "***REDACTED***" in result["secret"].iloc[0]
    assert result["safe"].iloc[0] == "hello"


# ---------------------------------------------------------------------------
# Tests: load_events
# ---------------------------------------------------------------------------


def test_load_events_missing_file(tmp_path: Path) -> None:
    df = load_events(tmp_path / "nope.jsonl")
    assert df.empty
    assert "event_id" in df.columns


def test_load_events_basic(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    rows = [_make_evo_event(proposal_id=f"p-{i}") for i in range(5)]
    _write_jsonl(path, rows)

    df = load_events(path)
    assert len(df) == 5
    assert "event_type" in df.columns
    assert "_ts" in df.columns


def test_load_events_time_filter(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    rows = [
        _make_evo_event(proposal_id="new", ts=datetime.now(timezone.utc).isoformat()),
        _make_evo_event(proposal_id="old", ts="2020-01-01T00:00:00+00:00"),
    ]
    _write_jsonl(path, rows)

    df = load_events(path, since_hours=24)
    assert len(df) == 1
    assert df.iloc[0]["proposal_id"] == "new"


def test_load_events_backward_compat_missing_fields(tmp_path: Path) -> None:
    """Old events without the new title/objective/rollback_plan fields."""
    path = tmp_path / "events.jsonl"
    old_event = {
        "event_id": "old-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "evolve_generated",
        "proposal_id": "p-legacy",
        "risk_level": "low",
    }
    _write_jsonl(path, [old_event])
    df = load_events(path)
    assert len(df) == 1
    assert "title" in df.columns
    assert "rollback_plan" in df.columns


# ---------------------------------------------------------------------------
# Tests: load_benchmarks
# ---------------------------------------------------------------------------


def test_load_benchmarks_missing_file(tmp_path: Path) -> None:
    df = load_benchmarks(tmp_path / "nope.jsonl")
    assert df.empty


def test_load_benchmarks_basic(tmp_path: Path) -> None:
    path = tmp_path / "bench.jsonl"
    _write_jsonl(path, [_make_bench_result(100), _make_bench_result(500, 80.0)])
    df = load_benchmarks(path)
    assert len(df) == 2


# ---------------------------------------------------------------------------
# Tests: flatten_stages
# ---------------------------------------------------------------------------


def test_flatten_stages_basic(tmp_path: Path) -> None:
    path = tmp_path / "bench.jsonl"
    _write_jsonl(path, [_make_bench_result(100)])
    df = load_benchmarks(path)
    flat = flatten_stages(df)
    assert len(flat) == 2
    assert "stage" in flat.columns
    assert set(flat["stage"]) == {"diagnosis", "gatekeeper"}


def test_flatten_stages_empty() -> None:
    import pandas as pd

    flat = flatten_stages(pd.DataFrame())
    assert flat.empty
