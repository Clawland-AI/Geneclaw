"""Run recorder — writes JSONL event logs for GEP v0 observability."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from geneclaw.models import RunEvent
from geneclaw.redact import redact_secrets


class RunRecorder:
    """Append-only JSONL recorder scoped to a session.

    Writes to ``<workspace>/geneclaw/runs/<session_key>/YYYYMMDD.jsonl``.
    """

    def __init__(
        self,
        workspace: Path,
        session_key: str,
        *,
        max_chars: int = 500,
        redact: bool = True,
    ) -> None:
        self._workspace = workspace
        self._session_key = session_key
        self._max_chars = max_chars
        self._redact = redact

        safe_key = session_key.replace(":", "_").replace("/", "_")
        self._run_dir = workspace / "geneclaw" / "runs" / safe_key
        self._run_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_path(self) -> Path:
        """Return today's JSONL file path."""
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return self._run_dir / f"{day}.jsonl"

    def _clip(self, text: str | None) -> str | None:
        if text is None:
            return None
        clipped = text[: self._max_chars]
        if self._redact:
            clipped = redact_secrets(clipped)
        return clipped

    def _write(self, event: RunEvent) -> None:
        path = self._log_path()
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_inbound(
        self, channel: str, session_key: str, preview: str
    ) -> None:
        """Record an inbound message event."""
        self._write(
            RunEvent(
                session_key=session_key,
                event_type="inbound_msg",
                channel=channel,
                preview=self._clip(preview),
            )
        )

    def record_tool_start(self, tool_name: str) -> float:
        """Record a tool-call start event.  Returns a monotonic timestamp."""
        self._write(
            RunEvent(
                session_key=self._session_key,
                event_type="tool_start",
                tool_name=tool_name,
            )
        )
        return time.monotonic()

    def record_tool_end(
        self,
        tool_name: str,
        start_mono: float,
        *,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Record a tool-call end event with duration."""
        dur = (time.monotonic() - start_mono) * 1000.0
        self._write(
            RunEvent(
                session_key=self._session_key,
                event_type="tool_end",
                tool_name=tool_name,
                duration_ms=round(dur, 2),
                success=success,
                error=self._clip(error),
            )
        )

    def record_exception(self, error: str) -> None:
        """Record an exception event."""
        self._write(
            RunEvent(
                session_key=self._session_key,
                event_type="exception",
                error=self._clip(error),
                success=False,
            )
        )

    def record_outbound(self, preview: str) -> None:
        """Record an outbound response event."""
        self._write(
            RunEvent(
                session_key=self._session_key,
                event_type="outbound_msg",
                preview=self._clip(preview),
            )
        )

    # ------------------------------------------------------------------
    # Read helpers (used by evolver)
    # ------------------------------------------------------------------

    def iter_events(self, max_events: int = 500) -> list[dict[str, Any]]:
        """Read recent events across all JSONL files in this session dir."""
        events: list[dict[str, Any]] = []
        files = sorted(self._run_dir.glob("*.jsonl"))
        for fp in files:
            for line in fp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events[-max_events:]

    @staticmethod
    def list_sessions(workspace: Path) -> list[str]:
        """List all session directories under the geneclaw/runs tree."""
        runs_dir = workspace / "geneclaw" / "runs"
        if not runs_dir.exists():
            return []
        return [p.name for p in runs_dir.iterdir() if p.is_dir()]
