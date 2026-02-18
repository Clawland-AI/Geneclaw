"""Tests for geneclaw evolver (M2)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from geneclaw.evolver import diagnose_events, generate_proposal, _minimal_fallback
from geneclaw.models import EvolutionProposal


# ---------------------------------------------------------------------------
# Heuristic diagnosis
# ---------------------------------------------------------------------------


def test_evolver_heuristic_finds_failures() -> None:
    """diagnose_events should count tool failures and exception clusters."""
    events = [
        {"event_type": "tool_end", "tool_name": "exec", "success": False, "error": "timeout"},
        {"event_type": "tool_end", "tool_name": "exec", "success": False, "error": "timeout"},
        {"event_type": "tool_end", "tool_name": "read_file", "success": True},
        {"event_type": "tool_end", "tool_name": "write_file", "success": False, "error": "permission denied"},
        {"event_type": "exception", "success": False, "error": "ValueError: bad input"},
        {"event_type": "exception", "success": False, "error": "ValueError: bad input"},
        {"event_type": "inbound_msg", "preview": "hello"},
    ]

    result = diagnose_events(events)

    assert result["failure_count"] == 5  # 3 tool failures + 2 exceptions
    assert result["top_failing_tools"]["exec"] == 2
    assert result["top_failing_tools"]["write_file"] == 1
    assert "ValueError: bad input" in result["exception_clusters"]
    assert result["exception_clusters"]["ValueError: bad input"] == 2
    assert "exec(2)" in result["summary"]


def test_evolver_heuristic_no_failures() -> None:
    """When no failures, diagnosis should report zero."""
    events = [
        {"event_type": "tool_end", "tool_name": "exec", "success": True},
        {"event_type": "inbound_msg", "preview": "hi"},
    ]

    result = diagnose_events(events)
    assert result["failure_count"] == 0
    assert result["summary"] == "No failures detected."


# ---------------------------------------------------------------------------
# JSON parse + repair
# ---------------------------------------------------------------------------


def test_evolver_json_parse_repair() -> None:
    """json_repair should handle slightly malformed JSON from LLM."""
    import json_repair

    # Trailing comma (common LLM mistake)
    raw = '{"id": "abc", "title": "fix timeout", "risk_level": "low",}'
    parsed = json_repair.loads(raw)
    assert isinstance(parsed, dict)
    assert parsed["title"] == "fix timeout"

    # Missing quotes on keys
    raw2 = '{id: "abc", title: "fix timeout"}'
    parsed2 = json_repair.loads(raw2)
    assert isinstance(parsed2, dict)
    assert parsed2["id"] == "abc"


# ---------------------------------------------------------------------------
# Full proposal generation (with mocked LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_proposal_with_mock_llm(tmp_path) -> None:
    """generate_proposal should produce a valid EvolutionProposal from LLM output."""
    # Set up a session with some failure events
    from geneclaw.recorder import RunRecorder

    rec = RunRecorder(workspace=tmp_path, session_key="test:s1", redact=False)
    rec.record_inbound("cli", "test:s1", "test msg")
    start = rec.record_tool_start("exec")
    rec.record_tool_end("exec", start, success=False, error="timeout after 60s")
    rec.record_exception("RuntimeError: exec failed")

    # Mock LLM provider
    proposal_json = json.dumps({
        "id": str(uuid.uuid4()),
        "title": "increase exec timeout",
        "objective": "Prevent exec tool timeouts by increasing default timeout",
        "evidence": ["exec tool failed 1 time with timeout"],
        "risk_level": "low",
        "files_touched": ["nanobot/config/schema.py"],
        "unified_diff": "--- a/nanobot/config/schema.py\n+++ b/nanobot/config/schema.py\n@@ -1 +1 @@\n-    timeout: int = 60\n+    timeout: int = 120\n",
        "tests_to_run": ["pytest tests/test_geneclaw_evolver.py"],
        "rollback_plan": "Revert timeout to 60",
    })

    mock_response = MagicMock()
    mock_response.content = proposal_json

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    proposal = await generate_proposal(
        workspace=tmp_path,
        provider=mock_provider,
        model="test-model",
    )

    assert isinstance(proposal, EvolutionProposal)
    assert proposal.title == "increase exec timeout"
    assert proposal.risk_level == "low"
    assert len(proposal.files_touched) == 1


@pytest.mark.asyncio
async def test_generate_proposal_fallback_on_bad_llm(tmp_path) -> None:
    """If LLM returns garbage, generate_proposal should return a no-op fallback."""
    mock_response = MagicMock()
    mock_response.content = "This is not JSON at all!!!"

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    proposal = await generate_proposal(
        workspace=tmp_path,
        provider=mock_provider,
        model="test-model",
    )

    assert isinstance(proposal, EvolutionProposal)
    assert proposal.title == "no-op"


def test_minimal_fallback() -> None:
    """_minimal_fallback should return a safe no-op proposal."""
    diag = {"summary": "exec(3) failures", "failure_count": 3}
    proposal = _minimal_fallback(diag)
    assert proposal.title == "no-op"
    assert proposal.risk_level == "low"
    assert "exec(3)" in proposal.evidence[0]
