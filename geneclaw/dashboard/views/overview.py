"""Overview page — KPI cards, risk distribution, top files, recent events."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from geneclaw.dashboard.loader import load_benchmarks, load_events

TIME_OPTIONS = {"Last 24 h": 24, "Last 7 d": 168, "Last 30 d": 720, "All time": None}


def render(events_file: Path, benchmarks_file: Path) -> None:
    st.header("Overview")

    col_time, _ = st.columns([3, 9])
    with col_time:
        time_label = st.selectbox("Time range", list(TIME_OPTIONS.keys()))
    since = TIME_OPTIONS[time_label]

    df = load_events(events_file, since_hours=since)

    if df.empty:
        st.info("No events found. Run `nanobot geneclaw evolve --dry-run` to generate data.")
        return

    evolve = df[df["event_type"] == "evolve_generated"]
    apply_ok = df[df["event_type"] == "apply_succeeded"]
    apply_fail = df[df["event_type"] == "apply_failed"]
    apply_attempt = df[df["event_type"] == "apply_attempted"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Proposals", len(evolve))
    c2.metric("Apply Attempted", len(apply_attempt))
    c3.metric("Apply Succeeded", len(apply_ok))
    rate = (
        f"{len(apply_ok) / len(apply_attempt) * 100:.0f}%"
        if len(apply_attempt) > 0
        else "N/A"
    )
    c4.metric("Success Rate", rate)

    col_risk, col_files = st.columns(2)

    with col_risk:
        st.subheader("Risk Distribution")
        risk_counts = df["risk_level"].value_counts()
        if not risk_counts.empty:
            st.bar_chart(risk_counts)
        else:
            st.caption("No risk data")

    with col_files:
        st.subheader("Top Files Touched")
        all_files: list[str] = []
        for ft in df["files_touched"]:
            if isinstance(ft, list):
                all_files.extend(ft)
        if all_files:
            file_series = pd.Series(all_files).value_counts().head(10)
            st.dataframe(file_series.reset_index().rename(
                columns={"index": "File", 0: "Count"}
            ), use_container_width=True)
        else:
            st.caption("No file data")

    st.subheader("Recent Events (last 20)")
    display_cols = [
        c for c in ["timestamp", "event_type", "risk_level", "proposal_id", "result", "title"]
        if c in df.columns
    ]
    st.dataframe(df[display_cols].head(20), use_container_width=True)
