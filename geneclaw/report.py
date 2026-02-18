"""Report — aggregation and statistics for evolution events (GEP v0).

All functions are read-only and produce structured data for CLI display.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReportData:
    """Aggregated statistics from evolution events and run logs."""

    evolve_count: int = 0
    apply_attempted: int = 0
    apply_succeeded: int = 0
    apply_failed: int = 0
    success_rate: float = 0.0
    risk_distribution: dict[str, int] = field(default_factory=dict)
    top_files_touched: list[tuple[str, int]] = field(default_factory=list)
    top_tool_failures: list[tuple[str, int]] = field(default_factory=list)
    top_exceptions: list[tuple[str, int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON output."""
        return {
            "evolve_count": self.evolve_count,
            "apply_attempted": self.apply_attempted,
            "apply_succeeded": self.apply_succeeded,
            "apply_failed": self.apply_failed,
            "success_rate": self.success_rate,
            "risk_distribution": self.risk_distribution,
            "top_files_touched": [
                {"file": f, "count": c} for f, c in self.top_files_touched
            ],
            "top_tool_failures": [
                {"tool": t, "count": c} for t, c in self.top_tool_failures
            ],
            "top_exceptions": [
                {"error_prefix": e, "count": c} for e, c in self.top_exceptions
            ],
        }


def generate_report(
    evo_events: list[dict[str, Any]],
    run_events: list[dict[str, Any]] | None = None,
    *,
    top_n: int = 5,
) -> ReportData:
    """Aggregate evolution events and optional run events into a report.

    Parameters
    ----------
    evo_events:
        List of EvoEvent dicts from EventStore.
    run_events:
        Optional list of RunEvent dicts from RunRecorder (for tool failure stats).
    top_n:
        Number of top items to return in rankings.
    """
    report = ReportData()

    # --- Evolution event stats ---
    risk_counter: Counter[str] = Counter()
    files_counter: Counter[str] = Counter()

    for ev in evo_events:
        etype = ev.get("event_type", "")
        if etype == "evolve_generated":
            report.evolve_count += 1
        elif etype == "apply_attempted":
            report.apply_attempted += 1
        elif etype == "apply_succeeded":
            report.apply_succeeded += 1
        elif etype == "apply_failed":
            report.apply_failed += 1

        risk = ev.get("risk_level", "low")
        risk_counter[risk] += 1

        for fp in ev.get("files_touched", []):
            files_counter[fp] += 1

    total_applies = report.apply_succeeded + report.apply_failed
    if total_applies > 0:
        report.success_rate = report.apply_succeeded / total_applies * 100.0

    report.risk_distribution = dict(risk_counter)
    report.top_files_touched = files_counter.most_common(top_n)

    # --- Run event stats (tool failures / exceptions) ---
    if run_events:
        tool_failures: Counter[str] = Counter()
        exception_msgs: Counter[str] = Counter()

        for rev in run_events:
            rtype = rev.get("event_type", "")
            if rtype == "tool_end" and rev.get("success") is False:
                tool_name = rev.get("tool_name") or "unknown"
                tool_failures[tool_name] += 1
            if rtype == "exception":
                err = rev.get("error") or "unknown"
                exception_msgs[err[:80]] += 1

        report.top_tool_failures = tool_failures.most_common(top_n)
        report.top_exceptions = exception_msgs.most_common(top_n)

    return report
