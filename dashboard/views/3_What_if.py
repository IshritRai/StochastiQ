"""Scenario simulation (build-spec.md section 3.3, L1): sliders on control
coverage, reruns with the SAME random draws via apply_controls(), shows
delta-EAL/delta-VaR95. No number here is invented -- every figure comes from
a fresh engine run (CLAUDE.md rule 1).
"""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import apply_controls, run_scenario
from dashboard.format_utils import format_inr
from dashboard.theme import page_header
from dashboard.whatif_logic import build_overrides, paired_delta_eal_ci, paired_stats

page_header(
    "What-if: Control Scenario Simulation",
    "Slide control coverage and efficacy, then re-simulate with the same random draws to see \u0394EAL.",
    icon="\U0001f39b\ufe0f",
    eyebrow="What-if",
)

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

slider_defaults: dict[str, int] = {}
slider_values: dict[str, int] = {}
cols = st.columns(len(control_types))
for col, (ct_id, ct) in zip(cols, control_types.items()):
    baseline_pct = measured_coverage[ct_id] * 100
    default_pct = round(baseline_pct)
    slider_defaults[ct_id] = default_pct
    with col:
        st.caption(f"{ct.name}\n\nMeasured: {baseline_pct:.0f}%")
        slider_values[ct_id] = st.slider(ct.name, 0, 100, default_pct, key=f"slider-{ct_id}")


overrides = build_overrides(slider_values, slider_defaults)

seed = settings.default_seed
baseline = run_scenario(scenario_id, overrides={}, seed=seed)
modified = apply_controls(scenario_id, control_overrides=overrides, seed=seed)

# Common random numbers (same seed, same iteration order) make baseline and
# modified PAIRED per iteration, so their difference is a proper per-draw
# delta-EAL sample -- a much tighter, more honest interval than P10-P90 of
# either side's raw annual-loss distribution (which is dominated by Poisson
# zero-inflation, not by uncertainty in the control's effect).
delta_eal, delta_ci_low, delta_ci_high = paired_delta_eal_ci(baseline.loss_vector, modified.loss_vector)
delta_var95 = modified.summary.var95 - baseline.summary.var95

baseline_stats = paired_stats(baseline.loss_vector)
modified_stats = paired_stats(modified.loss_vector)

col1, col2, col3 = st.columns(3)
col1.metric("Baseline EAL", format_inr(baseline.summary.eal))
col1.caption(
    f"P(any loss): {baseline_stats['p_any_loss']:.1%} · "
    f"Loss | event: {format_inr(baseline_stats['loss_given_event'])} · "
    f"VaR99: {format_inr(baseline_stats['var99'])}"
)
col2.metric(
    "What-if EAL",
    format_inr(modified.summary.eal),
    delta=format_inr(delta_eal),
    delta_color="inverse",
)
col2.caption(
    f"Δ-EAL P10–P90 (paired): {format_inr(delta_ci_low)} – {format_inr(delta_ci_high)}"
)
col3.metric(
    "What-if VaR95",
    format_inr(modified.summary.var95),
    delta=format_inr(delta_var95),
    delta_color="inverse",
)
col3.caption(
    f"P(any loss): {modified_stats['p_any_loss']:.1%} · "
    f"Loss | event: {format_inr(modified_stats['loss_given_event'])} · "
    f"VaR99: {format_inr(modified_stats['var99'])}"
)

st.caption(
    f"Baseline run `{baseline.run_id}`, what-if run `{modified.run_id}`, both seed={seed} "
    "(common random numbers, so a no-change slider gives exactly delta-EAL = 0). "
    "The Δ-EAL P10-P90 range comes from the PAIRED per-iteration difference "
    "(modified minus baseline, same random draws), not from either side's raw "
    "annual-loss spread (build-spec.md section 3.5)."
)
