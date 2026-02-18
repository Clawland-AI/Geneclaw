"""Tests for geneclaw event_store and report (M4.2)."""

from __future__ import annotations

import json
from pathlib import Path

from geneclaw.event_store import EventStore
from geneclaw.models import EvoEvent
from geneclaw.report import generate_report, ReportData


# ---------------------------------------------------------------------------
# EventStore
# ---------------------------------------------------------------------------


def test_event_store_writes_jsonl(tmp_path: Path) -> None:
    """EventStore should append events to a JSONL file."""
    store = EventStore(tmp_path, redact=False)

    ev1 = EvoEvent(
        event_type="evolve_generated",
        proposal_id="p1",
        risk_level="low",
        files_touched=["nanobot/agent/loop.py"],
        diff_lines=10,
        result="ok",
    )
    ev2 = EvoEvent(
        event_type="apply_attempted",
        proposal_id="p1",
        parent_event_id=ev1.event_id,
    )
    store.record(ev1)
    store.record(ev2)

    assert store.path.exists()
    lines = store.path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["event_type"] == "evolve_generated"
    assert parsed[0]["proposal_id"] == "p1"
    assert parsed[1]["event_type"] == "apply_attempted"
    assert parsed[1]["parent_event_id"] == ev1.event_id


def test_event_store_redacts_secrets(tmp_path: Path) -> None:
    """When redact=True, secrets in result field should be masked."""
    store = EventStore(tmp_path, redact=True)

    ev = EvoEvent(
        event_type="apply_failed",
        proposal_id="p2",
        result='fail: api_key="sk-supersecretkey12345678" leaked',
    )
    store.record(ev)

    content = store.path.read_text(encoding="utf-8")
    assert "sk-supersecretkey12345678" not in content
    assert "REDACTED" in content


def test_event_store_iter_events(tmp_path: Path) -> None:
    """iter_events should return all stored events."""
    store = EventStore(tmp_path, redact=False)
    for i in range(5):
        store.record(EvoEvent(event_type="evolve_generated", proposal_id=f"p{i}"))

    events = store.iter_events()
    assert len(events) == 5


def test_event_store_iter_empty(tmp_path: Path) -> None:
    """iter_events on empty store should return empty list."""
    store = EventStore(tmp_path, redact=False)
    assert store.iter_events() == []


def test_event_store_parent_chain(tmp_path: Path) -> None:
    """Events should support parent_event_id for tree structure."""
    store = EventStore(tmp_path, redact=False)

    root = EvoEvent(event_type="evolve_generated", proposal_id="p1")
    child = EvoEvent(
        event_type="apply_attempted",
        proposal_id="p1",
        parent_event_id=root.event_id,
    )
    grandchild = EvoEvent(
        event_type="apply_succeeded",
        proposal_id="p1",
        parent_event_id=child.event_id,
    )
    store.record(root)
    store.record(child)
    store.record(grandchild)

    events = store.iter_events()
    assert events[0]["parent_event_id"] == ""
    assert events[1]["parent_event_id"] == root.event_id
    assert events[2]["parent_event_id"] == child.event_id


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_report_aggregation() -> None:
    """generate_report should correctly aggregate evolution events."""
    evo_events = [
        {"event_type": "evolve_generated", "risk_level": "low", "files_touched": ["a.py", "b.py"]},
        {"event_type": "evolve_generated", "risk_level": "medium", "files_touched": ["a.py"]},
        {"event_type": "apply_attempted", "risk_level": "low", "files_touched": []},
        {"event_type": "apply_succeeded", "risk_level": "low", "files_touched": ["a.py"]},
        {"event_type": "apply_attempted", "risk_level": "medium", "files_touched": []},
        {"event_type": "apply_failed", "risk_level": "medium", "files_touched": ["c.py"]},
    ]

    run_events = [
        {"event_type": "tool_end", "tool_name": "exec", "success": False},
        {"event_type": "tool_end", "tool_name": "exec", "success": False},
        {"event_type": "tool_end", "tool_name": "read_file", "success": True},
        {"event_type": "exception", "error": "ValueError: oops"},
    ]

    report = generate_report(evo_events, run_events)

    assert report.evolve_count == 2
    assert report.apply_attempted == 2
    assert report.apply_succeeded == 1
    assert report.apply_failed == 1
    assert report.success_rate == 50.0

    assert report.risk_distribution["low"] >= 2
    assert report.risk_distribution["medium"] >= 2

    # a.py should be the most touched file
    top_file_names = [f for f, _ in report.top_files_touched]
    assert "a.py" in top_file_names

    # exec should be top failing tool
    assert report.top_tool_failures[0] == ("exec", 2)

    # exception cluster
    assert report.top_exceptions[0][0] == "ValueError: oops"


def test_report_empty_events() -> None:
    """Report with no events should return zero stats."""
    report = generate_report([], [])
    assert report.evolve_count == 0
    assert report.apply_attempted == 0
    assert report.success_rate == 0.0
    assert report.top_files_touched == []
    assert report.top_tool_failures == []


def test_report_no_applies() -> None:
    """When there are evolves but no applies, success_rate should be 0."""
    evo_events = [
        {"event_type": "evolve_generated", "risk_level": "low", "files_touched": ["x.py"]},
    ]
    report = generate_report(evo_events)
    assert report.evolve_count == 1
    assert report.success_rate == 0.0


def test_report_data_to_dict() -> None:
    """ReportData.to_dict() should produce a JSON-serializable dict."""
    evo_events = [
        {"event_type": "evolve_generated", "risk_level": "low", "files_touched": ["a.py"]},
        {"event_type": "apply_attempted", "risk_level": "low", "files_touched": []},
        {"event_type": "apply_succeeded", "risk_level": "low", "files_touched": ["a.py"]},
    ]
    run_events = [
        {"event_type": "tool_end", "tool_name": "exec", "success": False},
        {"event_type": "exception", "error": "RuntimeError: boom"},
    ]
    report = generate_report(evo_events, run_events)
    d = report.to_dict()

    assert d["evolve_count"] == 1
    assert d["apply_attempted"] == 1
    assert d["apply_succeeded"] == 1
    assert d["apply_failed"] == 0
    assert d["success_rate"] == 100.0
    assert d["risk_distribution"] == {"low": 3}
    assert any(f["file"] == "a.py" for f in d["top_files_touched"])
    assert any(t["tool"] == "exec" for t in d["top_tool_failures"])
    assert any(e["error_prefix"].startswith("RuntimeError") for e in d["top_exceptions"])

    serialized = json.dumps(d)
    assert isinstance(json.loads(serialized), dict)


def test_report_data_to_dict_empty() -> None:
    """to_dict() on empty report should produce valid JSON with zero values."""
    report = generate_report([], [])
    d = report.to_dict()

    assert d["evolve_count"] == 0
    assert d["top_files_touched"] == []
    assert d["top_tool_failures"] == []
    assert d["top_exceptions"] == []
    assert json.dumps(d)  # must be serializable
