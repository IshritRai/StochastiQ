"""Scenario simulation (build-spec.md section 3.3, L1): sliders on control
coverage, reruns with the SAME random draws via apply_controls(), shows
delta-EAL/delta-VaR95. No number here is invented -- every figure comes from
a fresh engine run (CLAUDE.md rule 1).
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import apply_controls, run_scenario
from dashboard.format_utils import format_inr

st.set_page_config(page_title="What-if | StochastiQ", layout="wide")
st.title("What-if: Control Scenario Simulation")

with session_scope() as session:
    scenarios = session.query(m.ThreatScenario).filter_by(active=True).all()
    scenario_options = {s.name: s.id for s in scenarios}

if not scenario_options:
    st.warning("No scenarios found. Run `make seed` to populate the database first.")
    st.stop()

scenario_name = st.selectbox("Scenario", list(scenario_options.keys()))
scenario_id = scenario_options[scenario_name]

with session_scope() as session:
    linked_effects = (
        session.query(m.ScenarioControlEffect).filter_by(scenario_id=scenario_id).all()
    )
    control_type_ids = sorted({e.control_type_id for e in linked_effects})
    control_types = {ct_id: session.get(m.ControlType, ct_id) for ct_id in control_type_ids}
    measured_coverage = {}
    for ct_id in control_type_ids:
        states = session.query(m.ControlState).filter_by(control_type_id=ct_id).all()
        measured_coverage[ct_id] = (
            sum(s.coverage_pct for s in states) / len(states) if states else 0.0
        )

if not control_types:
    st.info("This scenario has no linked controls yet (PLAN.md Task 6+ extends this).")
    st.stop()

st.write("Adjust control coverage below and compare against the measured baseline.")

overrides = {}
cols = st.columns(len(control_types))
for col, (ct_id, ct) in zip(cols, control_types.items()):
    baseline_pct = measured_coverage[ct_id] * 100
    with col:
        st.caption(f"{ct.name}\n\nMeasured: {baseline_pct:.0f}%")
        new_pct = st.slider(ct.name, 0, 100, round(baseline_pct), key=f"slider-{ct_id}")
        overrides[ct_id] = new_pct / 100.0

def _p10_p90(loss_vector: np.ndarray) -> tuple[float, float]:
    p10, p90 = np.percentile(loss_vector, [10, 90])
    return float(p10), float(p90)


seed = settings.default_seed
baseline = run_scenario(scenario_id, overrides={}, seed=seed)
modified = apply_controls(scenario_id, control_overrides=overrides, seed=seed)

baseline_p10, baseline_p90 = _p10_p90(baseline.loss_vector)
modified_p10, modified_p90 = _p10_p90(modified.loss_vector)
delta_eal = modified.summary.eal - baseline.summary.eal
delta_var95 = modified.summary.var95 - baseline.summary.var95

col1, col2, col3 = st.columns(3)
col1.metric("Baseline EAL", format_inr(baseline.summary.eal))
col1.caption(f"P10–P90: {format_inr(baseline_p10)} – {format_inr(baseline_p90)}")
col2.metric(
    "What-if EAL",
    format_inr(modified.summary.eal),
    delta=format_inr(delta_eal),
    delta_color="inverse",
)
col2.caption(f"P10–P90: {format_inr(modified_p10)} – {format_inr(modified_p90)}")
col3.metric(
    "What-if VaR95",
    format_inr(modified.summary.var95),
    delta=format_inr(delta_var95),
    delta_color="inverse",
)
col3.caption(
    f"Δ P10–P90: {format_inr(modified_p10 - baseline_p10)} – "
    f"{format_inr(modified_p90 - baseline_p90)}"
)

st.caption(
    f"Baseline run `{baseline.run_id}`, what-if run `{modified.run_id}`, both seed={seed} "
    "(common random numbers, so a no-change slider gives exactly delta-EAL = 0). "
    "Ranges shown are P10-P90 of the simulated annual-loss distribution, not false precision "
    "on a single number (build-spec.md section 3.5)."
)
