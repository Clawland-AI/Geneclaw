"""Geneclaw Dashboard — Streamlit entry point (read-only).

Launch via:
    nanobot geneclaw dashboard
    # or directly:
    streamlit run geneclaw/dashboard/app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Geneclaw Dashboard",
    page_icon="\U0001f9ec",
    layout="wide",
)

WORKSPACE = Path(os.environ.get("GENECLAW_WORKSPACE", "."))
EVENTS_FILE = Path(
    os.environ.get(
        "GENECLAW_EVENTS_FILE",
        str(WORKSPACE / "geneclaw" / "events" / "events.jsonl"),
    )
)
BENCHMARKS_FILE = Path(
    os.environ.get(
        "GENECLAW_BENCHMARKS_FILE",
        str(WORKSPACE / "geneclaw" / "benchmarks" / "benchmarks.jsonl"),
    )
)

PAGE_OVERVIEW = "Overview"
PAGE_TIMELINE = "Event Timeline"
PAGE_AUDIT = "Proposal Audit"
PAGE_BENCHMARKS = "Benchmarks"

st.sidebar.title("\U0001f9ec Geneclaw Dashboard")
page = st.sidebar.radio("Navigate", [PAGE_OVERVIEW, PAGE_TIMELINE, PAGE_AUDIT, PAGE_BENCHMARKS])
st.sidebar.markdown("---")
st.sidebar.caption("Read-only · No writes · No secrets")

if page == PAGE_OVERVIEW:
    from geneclaw.dashboard.views.overview import render
    render(EVENTS_FILE, BENCHMARKS_FILE)
elif page == PAGE_TIMELINE:
    from geneclaw.dashboard.views.timeline import render
    render(EVENTS_FILE)
elif page == PAGE_AUDIT:
    from geneclaw.dashboard.views.audit import render
    render(EVENTS_FILE)
elif page == PAGE_BENCHMARKS:
    from geneclaw.dashboard.views.benchmarks import render
    render(BENCHMARKS_FILE)
