"""Event store — append-only JSONL for evolution lifecycle events (GEP v0).

Writes to ``<workspace>/geneclaw/events/events.jsonl``.
All text is redacted before writing to prevent secret leaks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from geneclaw.models import EvoEvent
from geneclaw.redact import redact_secrets


class EventStore:
    """Append-only event log for geneclaw evolution lifecycle."""

    def __init__(self, workspace: Path, *, redact: bool = True) -> None:
        self._events_dir = workspace / "geneclaw" / "events"
        self._events_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._events_dir / "events.jsonl"
        self._redact = redact

    def record(self, event: EvoEvent) -> None:
        """Append a single event to the JSONL log."""
        line = event.model_dump_json()
        if self._redact:
            line = redact_secrets(line)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def iter_events(
        self, *, since_hours: float | None = None
    ) -> list[dict[str, Any]]:
        """Read events, optionally filtered by recency.

        Parameters
        ----------
        since_hours:
            If provided, only return events newer than ``now - since_hours``.
            Comparison is based on the ``timestamp`` field (ISO-8601 UTC).
        """
        if not self._path.exists():
            return []

        cutoff: datetime | None = None
        if since_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        events: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if cutoff is not None:
                ts_str = obj.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass  # include events with unparseable timestamps

            events.append(obj)
        return events

    @property
    def path(self) -> Path:
        return self._path
