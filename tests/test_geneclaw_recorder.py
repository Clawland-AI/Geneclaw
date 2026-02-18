"""Tests for geneclaw recorder and redaction (M1)."""

import json
from pathlib import Path

from geneclaw.recorder import RunRecorder
from geneclaw.redact import redact_secrets


def test_recorder_writes_jsonl(tmp_path: Path) -> None:
    """RunRecorder should create a JSONL file with structured events."""
    recorder = RunRecorder(
        workspace=tmp_path,
        session_key="test:session1",
        max_chars=200,
        redact=False,
    )

    recorder.record_inbound("cli", "test:session1", "hello world")
    start = recorder.record_tool_start("read_file")
    recorder.record_tool_end("read_file", start, success=True)
    start2 = recorder.record_tool_start("exec")
    recorder.record_tool_end("exec", start2, success=False, error="timeout")
    recorder.record_exception("ValueError: bad input")
    recorder.record_outbound("Here is my response")

    # Verify JSONL files exist
    run_dir = tmp_path / "geneclaw" / "runs" / "test_session1"
    assert run_dir.exists(), f"Run directory not created: {run_dir}"

    jsonl_files = list(run_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1, f"Expected 1 JSONL file, got {len(jsonl_files)}"

    lines = jsonl_files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 7, f"Expected 7 events, got {len(lines)}"

    events = [json.loads(line) for line in lines]

    # Check event types
    types = [e["event_type"] for e in events]
    assert types == [
        "inbound_msg",
        "tool_start",
        "tool_end",
        "tool_start",
        "tool_end",
        "exception",
        "outbound_msg",
    ]

    # Check tool_end has duration
    tool_end_event = events[2]
    assert tool_end_event["tool_name"] == "read_file"
    assert tool_end_event["duration_ms"] is not None
    assert tool_end_event["success"] is True

    # Check failed tool_end
    failed_end = events[4]
    assert failed_end["tool_name"] == "exec"
    assert failed_end["success"] is False
    assert "timeout" in (failed_end["error"] or "")

    # Check exception event
    exc_event = events[5]
    assert exc_event["success"] is False
    assert "bad input" in (exc_event["error"] or "")

    # iter_events should return all events
    loaded = recorder.iter_events()
    assert len(loaded) == 7


def test_recorder_clips_long_preview(tmp_path: Path) -> None:
    """Preview text should be clipped to max_chars."""
    recorder = RunRecorder(
        workspace=tmp_path,
        session_key="clip-test",
        max_chars=20,
        redact=False,
    )
    recorder.record_inbound("cli", "clip-test", "A" * 100)

    events = recorder.iter_events()
    assert len(events) == 1
    assert len(events[0]["preview"]) == 20


def test_recorder_list_sessions(tmp_path: Path) -> None:
    """list_sessions should find all session directories."""
    RunRecorder(workspace=tmp_path, session_key="s1")
    RunRecorder(workspace=tmp_path, session_key="s2")

    sessions = RunRecorder.list_sessions(tmp_path)
    assert set(sessions) == {"s1", "s2"}


def test_redact_secrets() -> None:
    """redact_secrets should mask various secret patterns."""
    # API key in key=value format
    text = 'api_key="sk-abcdefghijklmnop1234"'
    result = redact_secrets(text)
    assert "sk-abcdefghijklmnop1234" not in result
    assert "REDACTED" in result

    # Bearer token
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc"
    result = redact_secrets(text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
    assert "REDACTED" in result

    # GitHub token
    text = "token is ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh1234"
    result = redact_secrets(text)
    assert "ghp_" not in result
    assert "REDACTED" in result

    # AWS key
    text = "AKIAIOSFODNN7EXAMPLE"
    result = redact_secrets(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result

    # PEM private key
    text = "-----BEGIN PRIVATE KEY-----\nMIIE...base64...\n-----END PRIVATE KEY-----"
    result = redact_secrets(text)
    assert "BEGIN PRIVATE KEY" not in result
    assert "REDACTED_PRIVATE_KEY" in result

    # Slack token
    text = "xoxb-1234567890-abcdefghij"
    result = redact_secrets(text)
    assert "xoxb-" not in result

    # Plain text should pass through unchanged
    text = "Hello world, this is normal text."
    assert redact_secrets(text) == text


def test_redact_secrets_with_recorder(tmp_path: Path) -> None:
    """When redact=True, secrets in previews should be masked."""
    recorder = RunRecorder(
        workspace=tmp_path,
        session_key="redact-test",
        max_chars=500,
        redact=True,
    )
    recorder.record_inbound(
        "cli",
        "redact-test",
        'my api_key="sk-supersecretkey12345678"',
    )
    events = recorder.iter_events()
    assert len(events) == 1
    assert "sk-supersecretkey12345678" not in (events[0]["preview"] or "")
    assert "REDACTED" in (events[0]["preview"] or "")
