"""Investment Optimization (build-spec.md section 3.4, L1): standalone ΔEAL
and ROSI per control option, 0/1 knapsack under a budget, joint
re-simulation shown alongside the knapsack's additive estimate, and the
Investment vs. Risk Reduction curve. Every number here comes from a fresh
engine run (CLAUDE.md rule 1) -- nothing is typed in.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.optimize.optimizer import GORDON_LOEB_FRACTION, budget_sweep, evaluate_options, optimize
from dashboard.format_utils import format_inr
from dashboard.theme import (
    CATEGORICAL,
    STATUS,
    apply_layout,
    inject_page_css,
    page_header,
    section_header,
    sidebar_brand,
)

st.set_page_config(page_title="Investment | StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
sidebar_brand()
page_header(
    "Investment Optimization",
    "ROSI per control, a 0/1 knapsack under a \u20b9 budget, and the joint re-simulated result.",
    icon="\U0001f4b0",
    eyebrow="Investment",
)

with session_scope() as session:
    options = session.query(m.ControlOption).all()

if not options:
    st.warning("No control options found. Run `make seed` to populate the database first.")
    st.stop()

seed = settings.default_seed
n_iter = settings.default_n_iter


@st.cache_data(ttl=300, show_spinner="Evaluating standalone control options...")
def _cached_evaluate_options(seed: int, n_iter: int):
    return evaluate_options(seed, n_iter)


baseline_eal, evaluations = _cached_evaluate_options(seed, n_iter)

section_header("Standalone ROSI per control option", icon="\U0001f4c8")
st.caption(
    "Each row uses the SAME random draws as the baseline (apply_controls' common "
    "random numbers), so a zero-effect option always shows delta-EAL = 0 exactly."
)
def _rosi_badge(rosi: float) -> str:
    color = STATUS["met"] if rosi >= 0 else STATUS["gap"]
    icon = "✓" if rosi >= 0 else "✕"
    return f'<span class="status-badge" style="background-color:{color};color:#ffffff;">{icon} {rosi:.0%}</span>'


eval_df = pd.DataFrame(
    [
        {
            "Control": ev.control_name,
            "Annualized cost": format_inr(ev.annual_cost),
            "Standalone ΔEAL": format_inr(ev.standalone_delta_eal),
            "ROSI": _rosi_badge(ev.rosi),
        }
        for ev in sorted(evaluations, key=lambda e: -e.standalone_delta_eal)
    ]
)
st.markdown(eval_df.to_html(escape=False, index=False), unsafe_allow_html=True)

section_header("Choose a set under a budget", icon="\U0001f9ee")
max_cost = sum(ev.annual_cost for ev in evaluations) or 1.0
_LAKH = 1_00_000
max_cost_lakh = max_cost / _LAKH
budget_lakh = st.slider(
    "Annual budget",
    min_value=0.0,
    max_value=float(max_cost_lakh),
    value=float(max_cost_lakh) * 0.3,
    step=max_cost_lakh / 100,
    format="₹%.2f L",
)
budget = budget_lakh * _LAKH
st.caption(f"Budget: {format_inr(budget)}")

plan = optimize(budget=budget, seed=seed, n_iter=n_iter, persist=False)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Baseline EAL", format_inr(plan.baseline_eal))
col2.metric(
    "Knapsack estimate (additive ΔEAL)",
    format_inr(plan.knapsack_delta_eal),
)
col3.metric(
    "Joint re-simulated ΔEAL",
    format_inr(plan.joint_delta_eal),
    delta=format_inr(plan.joint_delta_eal - plan.knapsack_delta_eal),
)
col4.metric(
    "Joint re-simulated ΔVaR99",
    format_inr(plan.joint_delta_var99),
)
st.caption(
    "The gap between the knapsack's additive estimate and the joint re-simulated result "
    "is expected when controls interact (build-spec.md section 3.4) -- it is shown, not hidden. "
    "ΔVaR99 is the reduction in the 99th-percentile annual loss from the SAME joint re-simulation, "
    "shown alongside ΔEAL since a control can move the tail without moving the mean much."
)

if plan.exceeds_gordon_loeb:
    st.warning(
        f"This budget exceeds ~37% of baseline EAL ({format_inr(plan.baseline_eal * GORDON_LOEB_FRACTION)}), "
        "the Gordon-Loeb heuristic ceiling. This is a heuristic, not a universal law -- "
        "see docs/research/fair-based-cyber-risk.md."
    )

st.write("Selected controls:")
if plan.selected:
    st.dataframe(
        [{"Control": ev.control_name, "Standalone ΔEAL": format_inr(ev.standalone_delta_eal)} for ev in plan.selected],
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No controls fit within this budget.")

section_header("Investment vs. Risk Reduction curve", icon="\U0001f4c9")


@st.cache_data(ttl=300, show_spinner="Sweeping the budget curve...")
def _cached_budget_sweep(seed: int, n_iter: int):
    return budget_sweep(seed=seed, n_points=8, n_iter=n_iter)


curve = _cached_budget_sweep(seed, n_iter)
curve_df = pd.DataFrame(curve, columns=["budget", "delta_eal"])
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=curve_df["budget"],
        y=curve_df["delta_eal"],
        mode="lines+markers",
        line={"color": CATEGORICAL["blue"], "width": 2},
        marker={"size": 8, "color": CATEGORICAL["blue"]},
        fill="tozeroy",
        fillcolor="rgba(42, 120, 214, 0.08)",
        hovertemplate="Budget: %{x:,.0f}<br>ΔEAL: %{y:,.0f}<extra></extra>",
    )
)
fig.update_layout(xaxis_title="Annual budget (INR)", yaxis_title="Best achievable ΔEAL (INR)")
apply_layout(fig, height=350)
st.plotly_chart(fig, width="stretch")
