"""Streamlit entry point. Pages live in dashboard/pages/ (PLAN.md Task 5):
Executive, Technical, What-if, Investment, Compliance.

Every figure must trace to a SIMULATION_RUN id once the engine (Task 3+)
lands -- no hard-coded numbers here (CLAUDE.md rule 1).
"""

from __future__ import annotations

import streamlit as st

from app.data import models as m
from app.data.db import session_scope
from app.nlq.router import answer
from dashboard.theme import inject_page_css

st.set_page_config(page_title="StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)

st.title("StochastiQ")
st.caption(
    "AI-powered continuous cyber risk quantification and investment optimization platform "
    "(SIH PS 26105). Company data is synthetic; the math, vulnerability intelligence, and "
    "framework catalogues are real."
)

with session_scope() as session:
    has_data = session.query(m.Organization).first() is not None

if not has_data:
    st.info("Run `make seed` to populate the database, then reload this page.")
    st.stop()

st.subheader("Ask a question")
st.caption(
    "Allow-listed Gemini tool-calling over the same 9 real engine/DB calls (PLAN.md "
    "Task 16) when GEMINI_API_KEY is set, phrasing only -- every number still comes from "
    "the structured tool result, never the model; falls back to the plain L1 keyword "
    "router otherwise. Questions outside the 9 supported intents get an honest "
    "'I can't answer that yet.'"
)
question = st.text_input(
    "e.g. \"What is our highest financial cyber risk today?\"", key="nlq_question"
)
if question:
    result = answer(question)
    st.write(result.text)
    if result.provenance:
        st.caption(f"Source: {result.provenance}")

st.info("See the pages in the sidebar: Executive, Technical, What-if, Investment, Compliance.")
