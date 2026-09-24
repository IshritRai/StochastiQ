"""Investment Optimization (build-spec.md section 3.4). Lands in PLAN.md
Task 11 (0/1 knapsack over CONTROL_OPTION, joint re-simulation, budget-sweep
curve). Placeholder only -- no fabricated ROSI/budget numbers belong here
until the optimizer exists (CLAUDE.md rule 1)."""

from __future__ import annotations

import streamlit as st

from app.data import models as m
from app.data.db import session_scope

st.set_page_config(page_title="Investment | StochastiQ", layout="wide")
st.title("Investment Optimization")

st.info(
    "The optimizer (0/1 knapsack over control options, joint re-simulation, "
    "Investment vs. Risk Reduction curve) is PLAN.md Task 11. This page will "
    "show real ROSI and budget-curve numbers once that lands -- not before."
)

with session_scope() as session:
    options = session.query(m.ControlOption).all()

if options:
    st.subheader("Candidate control options (costs only -- no ROSI yet)")
    with session_scope() as session:
        rows = []
        for opt in options:
            ct = session.get(m.ControlType, opt.control_type_id)
            rows.append(
                {
                    "Control": ct.name if ct else opt.control_type_id,
                    "Target coverage": f"{opt.target_coverage:.0%}",
                    "Capex (INR)": f"{opt.capex:,.0f}",
                    "Opex/year (INR)": f"{opt.opex_per_year:,.0f}",
                }
            )
    st.dataframe(rows, hide_index=True, width="stretch")
