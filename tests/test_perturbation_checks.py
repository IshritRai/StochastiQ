"""Permanent regression tests for the perturbation-check findings recorded in
docs/L1_VERIFICATION.md items 1 and 2. These are not guardrail tests from
build-spec.md's R3 list -- they were caught by manually perturbing the real
UI (changing seeds/sliders and comparing pages) rather than by the original
automated suite, which is exactly why they're pinned here permanently.
"""

from __future__ import annotations

from app.engine.contracts import apply_controls, run_org, run_scenario
from dashboard.whatif_logic import build_overrides
from tests.conftest import make_scenario


def test_run_org_matches_run_scenario_for_same_seed(engine_db):
    """L1_VERIFICATION.md item 1: a scenario run standalone via run_scenario()
    must equal that SAME scenario's entry inside run_org()'s scenario_results,
    for the same top-level seed -- otherwise the Executive page (which uses
    run_org) and the What-if page (which uses run_scenario) silently disagree
    on the same scenario's EAL."""
    session = engine_db()
    make_scenario(session, "scenario-1", tef=(0.5, 1.0, 2.0), vuln=(0.2, 0.4, 0.6))
    session.commit()
    session.close()

    seed = 42
    standalone = run_scenario("scenario-1", overrides={}, seed=seed)
    org = run_org(overrides={"scenarios": ["scenario-1"]}, seed=seed)

    from_org = org.scenario_results["scenario-1"]
    assert from_org.summary.eal == standalone.summary.eal
    assert from_org.summary.var95 == standalone.summary.var95
    assert list(from_org.loss_vector) == list(standalone.loss_vector)


def test_untouched_slider_gives_exactly_zero_delta(engine_db):
    """L1_VERIFICATION.md item 2: leaving every What-if slider at its
    measured-baseline default must give delta-EAL exactly 0, through the same
    call path the UI uses (build_overrides -> apply_controls), not just
    through apply_controls() called directly with an empty dict."""
    session = engine_db()
    scenario = make_scenario(session, "scenario-1", vuln=(0.3, 0.5, 0.7))
    from app.data import models as m

    control_type = m.ControlType(
        name="MFA on privileged accounts",
        fair_category="resistive",
        factor_changed="Vuln",
        efficacy_low=0.6,
        efficacy_mode=0.8,
        efficacy_high=0.95,
        prior_source="test fixture",
        is_assumption=True,
    )
    session.add(control_type)
    session.flush()
    # A coverage whose *100 is NOT a whole number, so the slider's rounded
    # default (67) differs from the exact measured value (0.6666...) -- this
    # is the exact case that regressed before the build_overrides fix.
    session.add(m.ControlState(control_type_id=control_type.id, scope="org", coverage_pct=2 / 3))
    session.add(
        m.ScenarioControlEffect(
            scenario_id=scenario.id,
            control_type_id=control_type.id,
            factor="Vuln",
            effect_model="multiplicative",
        )
    )
    session.commit()
    session.close()

    seed = 7
    slider_defaults = {control_type.id: round((2 / 3) * 100)}
    slider_values = dict(slider_defaults)  # untouched: slider == its own default

    overrides = build_overrides(slider_values, slider_defaults)
    assert overrides == {}

    baseline = run_scenario("scenario-1", overrides={}, seed=seed)
    modified = apply_controls("scenario-1", control_overrides=overrides, seed=seed)

    assert modified.summary.eal == baseline.summary.eal
    assert list(modified.loss_vector) == list(baseline.loss_vector)
