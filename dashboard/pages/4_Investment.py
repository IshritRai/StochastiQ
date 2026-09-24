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

st.set_page_config(page_title="Investment | StochastiQ", layout="wide")
st.title("Investment Optimization")

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

st.subheader("Standalone ROSI per control option")
st.caption(
    "Each row uses the SAME random draws as the baseline (apply_controls' common "
    "random numbers), so a zero-effect option always shows delta-EAL = 0 exactly."
)
eval_df = pd.DataFrame(
    [
        {
            "Control": ev.control_name,
            "Annualized cost": format_inr(ev.annual_cost),
            "Standalone ΔEAL": format_inr(ev.standalone_delta_eal),
            "ROSI": f"{ev.rosi:.0%}",
        }
        for ev in sorted(evaluations, key=lambda e: -e.standalone_delta_eal)
    ]
)
st.dataframe(eval_df, hide_index=True, width="stretch")

st.subheader("Choose a set under a budget")
max_cost = sum(ev.annual_cost for ev in evaluations) or 1.0
budget = st.slider(
    "Annual budget (INR)", min_value=0.0, max_value=float(max_cost), value=float(max_cost) * 0.3, step=max_cost / 100
)
st.caption(f"Budget: {format_inr(budget)}")

plan = optimize(budget=budget, seed=seed, n_iter=n_iter, persist=False)

col1, col2, col3 = st.columns(3)
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
st.caption(
    "The gap between the knapsack's additive estimate and the joint re-simulated result "
    "is expected when controls interact (build-spec.md section 3.4) -- it is shown, not hidden."
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

st.subheader("Investment vs. Risk Reduction curve")


@st.cache_data(ttl=300, show_spinner="Sweeping the budget curve...")
def _cached_budget_sweep(seed: int, n_iter: int):
    return budget_sweep(seed=seed, n_points=8, n_iter=n_iter)


curve = _cached_budget_sweep(seed, n_iter)
curve_df = pd.DataFrame(curve, columns=["budget", "delta_eal"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=curve_df["budget"], y=curve_df["delta_eal"], mode="lines+markers"))
fig.update_layout(
    xaxis_title="Annual budget (INR)",
    yaxis_title="Best achievable ΔEAL (INR)",
    height=350,
    margin={"l": 10, "r": 10, "t": 10, "b": 10},
)
st.plotly_chart(fig, width="stretch")
