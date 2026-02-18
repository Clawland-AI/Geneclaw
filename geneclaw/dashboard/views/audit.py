"""Proposal Audit page — inspect proposal metadata from event records."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from geneclaw.dashboard.loader import load_events


def render(events_file: Path) -> None:
    st.header("Proposal Audit")

    df = load_events(events_file)
    if df.empty:
        st.info("No events found.")
        return

    proposals = df[df["event_type"] == "evolve_generated"].copy()
    if proposals.empty:
        st.info("No proposals recorded yet.")
        return

    proposal_ids = proposals["proposal_id"].tolist()
    selected_id = st.selectbox("Select Proposal", proposal_ids, key="audit_pid")

    row = proposals[proposals["proposal_id"] == selected_id].iloc[0]

    st.subheader(f"Proposal: {row.get('title', selected_id)}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Risk Level", row.get("risk_level", "—"))
    c2.metric("Diff Lines", row.get("diff_lines", 0))
    files = row.get("files_touched", [])
    c3.metric("Files Touched", len(files) if isinstance(files, list) else 0)

    st.markdown("**Objective**")
    st.text(row.get("objective", "(not recorded)") or "(not recorded)")

    st.markdown("**Files Touched**")
    if isinstance(files, list) and files:
        for f in files:
            st.code(f, language="text")
    else:
        st.caption("None recorded")

    tests = row.get("tests_to_run", [])
    st.markdown("**Tests to Run**")
    if isinstance(tests, list) and tests:
        for t in tests:
            st.code(t, language="bash")
    else:
        st.caption("None specified")

    st.markdown("**Rollback Plan**")
    st.text(row.get("rollback_plan", "(not recorded)") or "(not recorded)")

    st.markdown("**Result**")
    st.text(row.get("result", "—"))

    related = df[df["proposal_id"] == selected_id].sort_values("_ts")
    if len(related) > 1:
        st.subheader("Related Events")
        rel_cols = [
            c for c in ["timestamp", "event_type", "risk_level", "result"]
            if c in related.columns
        ]
        st.dataframe(related[rel_cols], use_container_width=True)
