"""PLAN.md Task 7: apply_controls with a real coverage change reduces EAL,
using the same seed as the baseline (common random numbers)."""

from __future__ import annotations

from app.data import models as m
from app.engine.contracts import apply_controls, run_scenario
from tests.conftest import make_scenario


def _link_control(session, scenario, coverage: float) -> str:
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

    session.add(m.ControlState(control_type_id=control_type.id, scope="org", coverage_pct=coverage))
    session.add(
        m.ScenarioControlEffect(
            scenario_id=scenario.id,
            control_type_id=control_type.id,
            factor="Vuln",
            effect_model="multiplicative",
        )
    )
    session.flush()
    return control_type.id


def test_improving_coverage_reduces_eal(engine_db):
    session = engine_db()
    scenario = make_scenario(session, "scenario-1", vuln=(0.3, 0.5, 0.7))
    control_type_id = _link_control(session, scenario, coverage=0.2)
    session.commit()
    session.close()

    baseline = run_scenario("scenario-1", overrides={}, seed=10)
    improved = apply_controls("scenario-1", control_overrides={control_type_id: 0.95}, seed=10)

    assert improved.summary.eal < baseline.summary.eal


def test_worsening_coverage_increases_eal(engine_db):
    session = engine_db()
    scenario = make_scenario(session, "scenario-1", vuln=(0.3, 0.5, 0.7))
    control_type_id = _link_control(session, scenario, coverage=0.8)
    session.commit()
    session.close()

    baseline = run_scenario("scenario-1", overrides={}, seed=11)
    worsened = apply_controls("scenario-1", control_overrides={control_type_id: 0.0}, seed=11)

    assert worsened.summary.eal > baseline.summary.eal
