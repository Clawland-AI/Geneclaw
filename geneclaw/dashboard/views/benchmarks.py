"""Benchmarks page — pipeline performance trends."""

from __future__ import annotations

from pathlib import Path

import plotly.express as px
import streamlit as st

from geneclaw.dashboard.loader import flatten_stages, load_benchmarks


def render(benchmarks_file: Path) -> None:
    st.header("Benchmarks")

    df = load_benchmarks(benchmarks_file)
    if df.empty:
        st.info(
            "No benchmark data found. Run:\n"
            "```\nnanobot geneclaw benchmark --save\n```"
        )
        return

    event_counts = sorted(df["event_count"].dropna().unique())
    if event_counts:
        selected_counts = st.multiselect(
            "Filter by event_count",
            event_counts,
            default=event_counts,
            key="bench_ec",
        )
        df = df[df["event_count"].isin(selected_counts)]

    st.subheader("Total Duration per Run")
    if "_ts" in df.columns and not df["_ts"].isna().all():
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["_ts"],
            y=df["total_duration_ms"],
            mode="lines+markers",
            name="total_duration_ms",
        ))
        fig.update_layout(
            xaxis_title="Run Time",
            yaxis_title="Duration (ms)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(df.set_index(df.index)["total_duration_ms"])

    stages_df = flatten_stages(df)
    if not stages_df.empty:
        st.subheader("Stage Breakdown")

        fig_stages = px.bar(
            stages_df,
            x="stage",
            y="avg_ms",
            color="event_count",
            barmode="group",
            title="Average ms per Stage",
            labels={"avg_ms": "Avg (ms)", "stage": "Stage"},
        )
        st.plotly_chart(fig_stages, use_container_width=True)

        st.subheader("Raw Stage Data")
        st.dataframe(stages_df, use_container_width=True)
    else:
        st.caption("No stage breakdown data available.")
