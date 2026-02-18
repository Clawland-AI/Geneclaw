"""Evolver — heuristic + LLM-assisted evolution proposal generator (GEP v0)."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json_repair

from geneclaw.models import EvolutionProposal, RunEvent
from geneclaw.recorder import RunRecorder


# ---------------------------------------------------------------------------
# Heuristic diagnosis
# ---------------------------------------------------------------------------


def diagnose_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyse run events and return a structured diagnosis.

    Returns a dict with:
        - ``failure_count``: total failures
        - ``top_failing_tools``: Counter of tool_name → failure count
        - ``exception_clusters``: Counter of error prefix → count
        - ``summary``: human-readable summary string
    """
    failure_count = 0
    tool_failures: Counter[str] = Counter()
    exception_msgs: Counter[str] = Counter()

    for raw in events:
        etype = raw.get("event_type", "")
        success = raw.get("success")

        if etype == "tool_end" and success is False:
            failure_count += 1
            tool_name = raw.get("tool_name") or "unknown"
            tool_failures[tool_name] += 1

        if etype == "exception":
            failure_count += 1
            err = raw.get("error") or "unknown"
            # Cluster by first 80 chars to group similar messages
            exception_msgs[err[:80]] += 1

    lines: list[str] = []
    if tool_failures:
        top = tool_failures.most_common(5)
        lines.append("Top failing tools: " + ", ".join(f"{n}({c})" for n, c in top))
    if exception_msgs:
        top = exception_msgs.most_common(5)
        lines.append("Exception clusters: " + ", ".join(f'"{m}"({c})' for m, c in top))

    return {
        "failure_count": failure_count,
        "top_failing_tools": dict(tool_failures),
        "exception_clusters": dict(exception_msgs),
        "summary": "; ".join(lines) if lines else "No failures detected.",
    }


# ---------------------------------------------------------------------------
# LLM proposal generation
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the Geneclaw Evolver — a self-improvement engine for the nanobot AI agent.

Given the diagnostic summary and optional conversation history snippets,
produce a single **evolution proposal** as a JSON object with EXACTLY these keys:

{
  "id": "<uuid4>",
  "title": "<short title>",
  "objective": "<what this evolution achieves>",
  "evidence": ["<evidence line 1>", ...],
  "risk_level": "low" | "medium" | "high",
  "files_touched": ["<relative file path>", ...],
  "unified_diff": "<valid unified diff string>",
  "tests_to_run": ["pytest <path>", ...],
  "rollback_plan": "<how to undo>"
}

Rules:
- Respond ONLY with the JSON object, no markdown fences, no commentary.
- Keep changes minimal and safe.
- Never modify .env, secrets, or .git files.
- Prefer fixes to the geneclaw/ or nanobot/ packages.
- If there is nothing to improve, return an object with id, title="no-op", and empty diff.
"""


def _build_user_prompt(
    diagnosis: dict[str, Any],
    history_snippet: str,
) -> str:
    parts = [
        "## Diagnosis",
        json.dumps(diagnosis, indent=2, ensure_ascii=False),
    ]
    if history_snippet:
        parts.append("## Recent History Snippet")
        parts.append(history_snippet[:4000])
    parts.append("\nGenerate the evolution proposal JSON now.")
    return "\n\n".join(parts)


def _minimal_fallback(diagnosis: dict[str, Any]) -> EvolutionProposal:
    """Return a safe no-op proposal when LLM output is unusable."""
    return EvolutionProposal(
        id=str(uuid.uuid4()),
        title="no-op",
        objective="LLM output was invalid; no evolution proposed.",
        evidence=[diagnosis.get("summary", "")],
        risk_level="low",
    )


async def generate_proposal(
    workspace: Path,
    provider: Any,
    model: str,
    *,
    session_keys: list[str] | None = None,
    since_hours: float = 24.0,
    max_events: int = 500,
) -> EvolutionProposal:
    """Generate an evolution proposal from recent run events.

    Parameters
    ----------
    workspace:
        Nanobot workspace path.
    provider:
        An ``LLMProvider`` instance (must have async ``chat()``).
    model:
        Model identifier string.
    session_keys:
        Limit to specific sessions; ``None`` = all.
    since_hours:
        How far back to look (not yet filtered — uses all available).
    max_events:
        Maximum events to load per session.

    Returns
    -------
    EvolutionProposal
    """
    # 1. Collect events
    all_events: list[dict[str, Any]] = []
    keys = session_keys or RunRecorder.list_sessions(workspace)
    for sk in keys:
        rec = RunRecorder(workspace=workspace, session_key=sk, redact=True)
        all_events.extend(rec.iter_events(max_events=max_events))

    # 2. Heuristic diagnosis
    diagnosis = diagnose_events(all_events)

    # 3. Gather history snippet
    history_snippet = ""
    history_file = workspace / "memory" / "HISTORY.md"
    if history_file.exists():
        content = history_file.read_text(encoding="utf-8")
        history_snippet = content[-4000:] if len(content) > 4000 else content

    # 4. LLM call
    user_prompt = _build_user_prompt(diagnosis, history_snippet)
    try:
        response = await provider.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
        )
        text = (response.content or "").strip()
        if not text:
            return _minimal_fallback(diagnosis)

        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = json_repair.loads(text)
        if not isinstance(parsed, dict):
            return _minimal_fallback(diagnosis)

        # Ensure required id
        if "id" not in parsed or not parsed["id"]:
            parsed["id"] = str(uuid.uuid4())

        return EvolutionProposal.model_validate(parsed)

    except Exception:
        return _minimal_fallback(diagnosis)
