"""Data loading, filtering, and redaction for the Geneclaw Dashboard.

All functions are pure readers — no writes, no side effects.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"""(?:api[_-]?key|token|secret|password|authorization|bearer)"""
        r"""[\s:="']*[\w/+\-]{8,}""",
        re.IGNORECASE,
    ),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"xoxb-[A-Za-z0-9\-]{24,}"),
]

_REDACT_PLACEHOLDER = "***REDACTED***"


def _redact_value(val: Any) -> Any:
    if not isinstance(val, str):
        return val
    result = val
    for pat in _SECRET_PATTERNS:
        result = pat.sub(_REDACT_PLACEHOLDER, result)
    return result


def redact_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply secret redaction to all string columns in a DataFrame."""
    if df.empty:
        return df
    obj_cols = df.select_dtypes(include=["object", "string"]).columns
    out = df.copy()
    for col in obj_cols:
        out[col] = out[col].apply(_redact_value)
    return out


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse a JSONL file, skipping malformed lines."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_events(
    path: Path | str,
    since_hours: float | None = None,
) -> pd.DataFrame:
    """Load EvoEvent records from a JSONL file into a DataFrame.

    Returns an empty DataFrame with expected columns when the file is
    missing, empty, or contains no parseable rows.
    """
    expected_cols = [
        "event_id", "timestamp", "event_type", "session_key",
        "proposal_id", "risk_level", "files_touched", "diff_lines",
        "tests_to_run", "parent_event_id", "result",
        "title", "objective", "rollback_plan",
    ]
    rows = _parse_jsonl(Path(path))
    if not rows:
        return pd.DataFrame(columns=expected_cols)

    df = pd.DataFrame(rows)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    if since_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        df = df[df["_ts"] >= cutoff]

    df = df.sort_values("_ts", ascending=False).reset_index(drop=True)
    return redact_dataframe(df)


def load_benchmarks(path: Path | str) -> pd.DataFrame:
    """Load BenchmarkResult records from a JSONL file into a DataFrame.

    Returns an empty DataFrame when the file is missing or contains
    no parseable rows.
    """
    expected_cols = [
        "timestamp", "event_count", "total_duration_ms", "stages",
    ]
    rows = _parse_jsonl(Path(path))
    if not rows:
        return pd.DataFrame(columns=expected_cols)

    df = pd.DataFrame(rows)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    if "timestamp" in df.columns:
        df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df = df.sort_values("_ts", ascending=False).reset_index(drop=True)
    return df


def flatten_stages(bench_df: pd.DataFrame) -> pd.DataFrame:
    """Expand the nested 'stages' list into one row per stage per benchmark run."""
    if bench_df.empty or "stages" not in bench_df.columns:
        return pd.DataFrame(columns=["timestamp", "stage", "duration_ms", "avg_ms", "iterations"])
    records: list[dict[str, Any]] = []
    for _, row in bench_df.iterrows():
        stages = row.get("stages")
        if not isinstance(stages, list):
            continue
        for s in stages:
            if isinstance(s, dict):
                records.append({
                    "timestamp": row.get("timestamp", ""),
                    "event_count": row.get("event_count", 0),
                    **s,
                })
    if not records:
        return pd.DataFrame(columns=["timestamp", "stage", "duration_ms", "avg_ms", "iterations"])
    return pd.DataFrame(records)
