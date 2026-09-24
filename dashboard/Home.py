"""Streamlit entry point. Pages live in dashboard/pages/ (PLAN.md Task 5):
Executive, Technical, What-if, Investment, Compliance.

Every figure must trace to a SIMULATION_RUN id once the engine (Task 3+)
lands -- no hard-coded numbers here (CLAUDE.md rule 1).
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="StochastiQ", layout="wide")

st.title("StochastiQ")
st.caption(
    "AI-powered continuous cyber risk quantification and investment optimization platform "
    "(SIH PS 26105). Company data is synthetic; the math, vulnerability intelligence, and "
    "framework catalogues are real."
)
st.info(
    "Dashboard pages are added as their backing engine functions are implemented "
    "(see PLAN.md, Task 5 onward). Run `make seed` to populate the database."
)
