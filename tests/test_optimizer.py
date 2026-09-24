"""PLAN.md Task 11 done-when test (build-spec.md section 3.4):
a zero-effect option gives ΔEAL exactly 0, and the budget curve never
decreases as budget grows. Joint re-simulation is always shown next to the
knapsack's additive estimate.
"""

from __future__ import annotations

from app.data import models as m
from app.optimize.optimizer import GORDON_LOEB_FRACTION, budget_sweep, evaluate_options, optimize
from tests.conftest import make_scenario


def _seed_two_scenarios_two_controls(session):
    make_scenario(session, "scenario-1", vuln=(0.3, 0.5, 0.7))
    make_scenario(session, "scenario-2", tef=(0.3, 0.6, 1.0), vuln=(0.2, 0.4, 0.6))

    effective_ct = m.ControlType(
        name="EDR coverage",
        fair_category="resistive",
        factor_changed="Vuln",
        efficacy_low=0.4,
        efficacy_mode=0.65,
        efficacy_high=0.85,
        prior_source="test fixture",
    )
    ineffective_ct = m.ControlType(
        name="Unlinked control",
        fair_category="resistive",
        factor_changed="Vuln",
        efficacy_low=0.5,
        efficacy_mode=0.7,
        efficacy_high=0.9,
        prior_source="test fixture",
    )
    session.add_all([effective_ct, ineffective_ct])
    session.flush()

    session.add(m.ControlState(control_type_id=effective_ct.id, scope="org", coverage_pct=0.2))
    session.add(
        m.ScenarioControlEffect(
            scenario_id="scenario-1", control_type_id=effective_ct.id, factor="Vuln", effect_model="multiplicative"
        )
    )
    # Note: no ScenarioControlEffect for ineffective_ct -- it exists but affects nothing.

    effective_option = m.ControlOption(
        control_type_id=effective_ct.id, scope="org", target_coverage=0.95, capex=300_000, opex_per_year=50_000, lifetime_years=3
    )
    zero_effect_option = m.ControlOption(
        control_type_id=ineffective_ct.id, scope="org", target_coverage=0.95, capex=100_000, opex_per_year=20_000, lifetime_years=3
    )
    session.add_all([effective_option, zero_effect_option])
    session.flush()
    return effective_option, zero_effect_option


def test_zero_effect_option_gives_exactly_zero_delta_eal(engine_db):
    session = engine_db()
    _effective, zero_effect = _seed_two_scenarios_two_controls(session)
    session.commit()
    session.close()

    _baseline_eal, evaluations = evaluate_options(seed=42, n_iter=5_000)
    zero_eval = next(e for e in evaluations if e.option_id == zero_effect.id)
    assert zero_eval.standalone_delta_eal == 0.0


def test_effective_option_gives_positive_delta_eal(engine_db):
    session = engine_db()
    effective, _zero_effect = _seed_two_scenarios_two_controls(session)
    session.commit()
    session.close()

    _baseline_eal, evaluations = evaluate_options(seed=42, n_iter=5_000)
    eff_eval = next(e for e in evaluations if e.option_id == effective.id)
    assert eff_eval.standalone_delta_eal > 0.0


def test_knapsack_respects_budget_and_shows_joint_result(engine_db):
    session = engine_db()
    effective, _zero_effect = _seed_two_scenarios_two_controls(session)
    session.commit()
    session.close()

    annual_cost_effective = 300_000 / 3 + 50_000
    plan = optimize(budget=annual_cost_effective + 1, seed=42, n_iter=5_000)

    selected_ids = {ev.option_id for ev in plan.selected}
    assert effective.id in selected_ids
    total_cost = sum(ev.annual_cost for ev in plan.selected)
    assert total_cost <= annual_cost_effective + 1 + 1e-6

    # Joint result is reported alongside the knapsack estimate, not hidden.
    assert isinstance(plan.joint_delta_eal, float)
    assert isinstance(plan.knapsack_delta_eal, float)


def test_gordon_loeb_flag(engine_db):
    session = engine_db()
    _seed_two_scenarios_two_controls(session)
    session.commit()
    session.close()

    baseline_eal, _ = evaluate_options(seed=42, n_iter=5_000)

    small_plan = optimize(budget=1.0, seed=42, n_iter=5_000, persist=False)
    assert small_plan.exceeds_gordon_loeb is False

    huge_plan = optimize(budget=baseline_eal * (GORDON_LOEB_FRACTION + 0.5), seed=42, n_iter=5_000, persist=False)
    assert huge_plan.exceeds_gordon_loeb is True


def test_budget_curve_never_decreases(engine_db):
    session = engine_db()
    _seed_two_scenarios_two_controls(session)
    session.commit()
    session.close()

    from itertools import pairwise

    points = budget_sweep(seed=42, n_points=6, n_iter=5_000)
    budgets = [b for b, _v in points]
    values = [v for _b, v in points]
    assert all(b2 >= b1 for b1, b2 in pairwise(budgets))
    assert all(v2 >= v1 - 1e-9 for v1, v2 in pairwise(values))
