"""Pydantic models for GEP v0 events and evolution proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    """A single runtime event recorded during an agent loop run."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp",
    )
    session_key: str = ""
    event_type: Literal[
        "inbound_msg",
        "tool_start",
        "tool_end",
        "exception",
        "outbound_msg",
    ] = "inbound_msg"
    channel: str | None = None
    tool_name: str | None = None
    duration_ms: float | None = None
    success: bool | None = None
    error: str | None = None
    preview: str | None = None


class EvolutionProposal(BaseModel):
    """A constrained evolution proposal (JSON + unified diff)."""

    id: str = ""
    title: str = ""
    objective: str = ""
    evidence: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    files_touched: list[str] = Field(default_factory=list)
    unified_diff: str = ""
    tests_to_run: list[str] = Field(default_factory=list)
    rollback_plan: str = ""


class EvoEvent(BaseModel):
    """A lifecycle event in the evolution pipeline (evolve/apply/report)."""

    event_id: str = Field(
        default_factory=lambda: __import__("uuid").uuid4().hex,
        description="Unique event identifier",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp",
    )
    event_type: Literal[
        "evolve_generated",
        "apply_attempted",
        "apply_succeeded",
        "apply_failed",
    ] = "evolve_generated"
    session_key: str = ""
    proposal_id: str = ""
    risk_level: Literal["low", "medium", "high"] = "low"
    files_touched: list[str] = Field(default_factory=list)
    diff_lines: int = 0
    tests_to_run: list[str] = Field(default_factory=list)
    parent_event_id: str = ""
    result: str = ""
    title: str = ""
    objective: str = ""
    rollback_plan: str = ""
