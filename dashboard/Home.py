"""Streamlit entry point / navigation shell.

This file owns everything that must run exactly once per interaction,
before any page's body: `st.set_page_config`, the shared stylesheet, the
sidebar brand mark, and the `st.navigation` route table itself, grouped
into sections so the sidebar reads as a designed IA (Overview / Risk /
Decisions) instead of Streamlit's flat auto-generated file list. Actual
page content lives in `dashboard/views/*.py`; each one only renders its
body (no `set_page_config`/CSS/brand calls there), since those already
ran here before `nav.run()` executes the selected page.

Every figure must trace to a SIMULATION_RUN id. No hard-coded numbers here.
"""

from __future__ import annotations

import streamlit as st

from dashboard.theme import inject_page_css, sidebar_brand

st.set_page_config(page_title="StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
sidebar_brand()

pages = {
    "Overview": [
        st.Page("views/0_Home.py", title="Home", icon="\U0001f3e0", url_path="home", default=True),
    ],
    "Risk": [
        st.Page("views/1_Executive.py", title="Executive", icon="\U0001f3af", url_path="executive"),
        st.Page("views/2_Technical.py", title="Technical", icon="\U0001f527", url_path="technical"),
        st.Page("views/3_What_if.py", title="What-if", icon="\U0001f39b️", url_path="what-if"),
    ],
    "Decisions": [
        st.Page("views/4_Investment.py", title="Investment", icon="\U0001f4b0", url_path="investment"),
        st.Page("views/5_Compliance.py", title="Compliance", icon="✅", url_path="compliance"),
    ],
}

nav = st.navigation(pages)
nav.run()
