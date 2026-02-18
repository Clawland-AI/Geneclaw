"""Event Timeline page — line/bar charts of evolve/apply activity."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from geneclaw.dashboard.loader import load_events

TIME_OPTIONS = {"Last 24 h": 24, "Last 7 d": 168, "Last 30 d": 720, "All time": None}
FREQ_OPTIONS = {"Hourly": "h", "Daily": "D"}


def render(events_file: Path) -> None:
    st.header("Event Timeline")

    c1, c2, c3 = st.columns([2, 2, 8])
    with c1:
        time_label = st.selectbox("Time range", list(TIME_OPTIONS.keys()), key="tl_time")
    with c2:
        freq_label = st.selectbox("Granularity", list(FREQ_OPTIONS.keys()), key="tl_freq")

    since = TIME_OPTIONS[time_label]
    freq = FREQ_OPTIONS[freq_label]

    risk_filter = st.multiselect(
        "Filter by risk level",
        ["low", "medium", "high"],
        default=["low", "medium", "high"],
        key="tl_risk",
    )

    df = load_events(events_file, since_hours=since)
    if df.empty:
        st.info("No events to display.")
        return

    df = df[df["risk_level"].isin(risk_filter)]
    if df.empty:
        st.info("No events match the selected filters.")
        return

    df["period"] = df["_ts"].dt.floor(freq)

    grouped = (
        df.groupby(["period", "event_type"])
        .size()
        .reset_index(name="count")
    )

    fig = px.bar(
        grouped,
        x="period",
        y="count",
        color="event_type",
        barmode="group",
        title="Events over Time",
        labels={"period": "Time", "count": "Count", "event_type": "Event Type"},
    )
    fig.update_layout(xaxis_tickformat="%Y-%m-%d %H:%M")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Event Detail")
    st.caption("Click a row to inspect.")
    display_cols = [
        c for c in ["timestamp", "event_type", "risk_level", "proposal_id", "result", "title"]
        if c in df.columns
    ]
    st.dataframe(df[display_cols].head(100), use_container_width=True)
