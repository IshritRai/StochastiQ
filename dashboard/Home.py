"""Streamlit entry point. Pages live in dashboard/pages/ (PLAN.md Task 5):
Executive, Technical, What-if, Investment, Compliance.

Every figure must trace to a SIMULATION_RUN id once the engine (Task 3+)
lands -- no hard-coded numbers here (CLAUDE.md rule 1).
"""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import run_org
from app.nlq.router import answer
from dashboard.format_utils import format_inr
from dashboard.theme import inject_page_css, page_header, section_header, sidebar_brand

st.set_page_config(page_title="StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
sidebar_brand()

with session_scope() as session:
    org_row = session.query(m.Organization).first()
    has_data = org_row is not None

if not has_data:
    page_header(
        "StochastiQ",
        "AI-powered continuous cyber risk quantification and investment optimization platform.",
        eyebrow="SIH PS 26105",
    )
    st.info("Run `make seed` to populate the database, then reload this page.")
    st.stop()

page_header(
    "StochastiQ",
    "Continuous cyber risk quantification and investment optimization, "
    f"for {org_row.name}. "
    "Company data is synthetic; the Monte Carlo math, vulnerability intelligence, "
    "and framework catalogues are real.",
    eyebrow="SIH PS 26105",
)

with st.container(border=True):
    st.markdown('<div class="sq-eyebrow">Ask StochastiQ</div>', unsafe_allow_html=True)
    st.caption(
        "Allow-listed Gemini tool-calling over 9 real engine/DB calls when `GEMINI_API_KEY` "
        "is set -- the model only phrases the answer, every number comes from the structured "
        "tool result, never the model itself. Falls back to a plain keyword router otherwise. "
        "Out-of-scope questions get an honest “I can't answer that yet” rather than a guess."
    )
    question = st.text_input(
        "Ask a question",
        placeholder='e.g. "What is our highest financial cyber risk today?"',
        key="nlq_question",
        label_visibility="collapsed",
    )
    if question:
        result = answer(question)
        st.markdown(f"**{result.text}**")
        if result.provenance:
            st.caption(f"Source: {result.provenance}")


@st.cache_data(ttl=300, show_spinner=False)
def _headline_numbers(seed: int, n_iter: int):
    org = run_org(overrides={"n_iter": n_iter}, seed=seed)
    return org.summary.eal, org.summary.var95, len(org.scenario_results)


eal, var95, n_scenarios = _headline_numbers(settings.default_seed, settings.default_n_iter)
n_assets = None
with session_scope() as _s:
    n_assets = _s.query(m.Asset).count()

section_header("At a glance", icon="\U0001f4ca")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Expected Annual Loss", format_inr(eal))
k2.metric("VaR95 (annual)", format_inr(var95))
k3.metric("Threat scenarios modeled", n_scenarios)
k4.metric("Assets in inventory", n_assets)
st.caption(
    "Same engine, same run contract as the Executive page -- these tiles are a preview, "
    "not a separate calculation."
)

section_header("Explore", icon="\U0001f9ed")
nav_cards = [
    ("pages/1_Executive.py", "\U0001f3af", "Executive", "EAL, VaR, loss exceedance curve, top risk contributors."),
    ("pages/2_Technical.py", "\U0001f527", "Technical", "Finding & asset inventory, remediation backlog, ageing."),
    ("pages/3_What_if.py", "\U0001f39b️", "What-if", "Slide control coverage and see ΔEAL re-simulate live."),
    ("pages/4_Investment.py", "\U0001f4b0", "Investment", "Knapsack-optimized control spend under a ₹ budget."),
    ("pages/5_Compliance.py", "✅", "Compliance", "NIST CSF status, incident-clock, ₹-at-risk per control."),
]
cols = st.columns(len(nav_cards))
for col, (target, icon, title, desc) in zip(cols, nav_cards, strict=True):
    with col:
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:1.6rem;">{icon}</div>'
                f'<div style="font-weight:700;margin-top:4px;">{title}</div>'
                f'<div style="font-size:0.82rem;color:#898781;margin-top:2px;min-height:52px;">{desc}</div>',
                unsafe_allow_html=True,
            )
            st.page_link(target, label="Open", icon="➡️")
