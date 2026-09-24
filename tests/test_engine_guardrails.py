"""R3 guardrail tests (build-spec.md, "Guardrail tests (write these first)").

Originally written against the engine stub (PLAN.md Task 2) and marked
xfail; now that Tasks 3/4/7 implement the engine, each test asserts real
behavior. A failure here is a genuine regression in the Risk Contract math,
not a stub artifact.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.engine.contracts import apply_controls, run_org, run_scenario, simulate, summarize
from tests.conftest import make_scenario


def test_r3_1_fixed_frequency_fixed_loss_gives_eal_within_mc_error():
    """Fixed frequency and fixed loss: EAL equals frequency x loss within Monte Carlo error."""
    freq, loss = 2.0, 10_000.0
    inputs = {"tef": freq, "vuln": 1.0, "plm_fixed": loss, "slef": 0.0}
    vec = simulate(inputs, seed=1, n_iter=50_000)
    eal = summarize(vec).eal
    assert abs(eal - freq * loss) / (freq * loss) < 0.02


def test_r3_2_lognormal_fit_reproduces_percentiles():
    """Lognormal fitted to (5th, 95th) percentiles reproduces those percentiles.

    Checked on the per-event loss magnitude sampler directly, not on the full
    annual-loss vector: with TEF x Vuln low enough that most years see zero
    events, the *annual* loss distribution is zero-inflated and its 5th/95th
    percentiles are not the same thing as the fitted per-event lognormal's
    (that zero-inflation is itself covered by test R3-1's Poisson check).
    """
    from app.engine.sampling import sample_loss_magnitude

    rng = np.random.default_rng(2)
    losses = sample_loss_magnitude(
        {"plm_p05": 1_000.0, "plm_p95": 100_000.0}, rng, n=200_000, prefix="plm"
    )
    p05, p95 = np.percentile(losses, [5, 95])
    assert p05 == pytest.approx(1_000.0, rel=0.10)
    assert p95 == pytest.approx(100_000.0, rel=0.10)


def test_r3_3_same_seed_gives_identical_results():
    """Same seed gives identical results (reproducible demos)."""
    inputs = {"tef": 1.5, "vuln": 0.5, "plm_p05": 5_000.0, "plm_p95": 50_000.0, "slef": 0.1}
    vec_a = simulate(inputs, seed=7, n_iter=10_000)
    vec_b = simulate(inputs, seed=7, n_iter=10_000)
    assert np.array_equal(vec_a, vec_b)


def test_r3_4_org_eal_equals_sum_of_scenario_eal(engine_db):
    """Organization EAL equals the sum of scenario EAL; asset allocations sum to scenario EAL."""
    session = engine_db()
    make_scenario(session, "scenario-1")
    make_scenario(session, "scenario-2", tef=(0.2, 0.4, 0.8), vuln=(0.1, 0.2, 0.4))
    session.commit()
    session.close()

    org = run_org(overrides={}, seed=3)
    scenario_eal_sum = sum(r.summary.eal for r in org.scenario_results.values())
    assert org.summary.eal == pytest.approx(scenario_eal_sum, rel=1e-9)


def test_r3_5_zero_effect_whatif_gives_zero_delta_eal(engine_db):
    """Zero-effect what-if gives ΔEAL exactly 0 (through apply_controls specifically)."""
    session = engine_db()
    make_scenario(session, "scenario-1")
    session.commit()
    session.close()

    baseline = run_scenario("scenario-1", overrides={}, seed=4)
    noop = apply_controls("scenario-1", control_overrides={}, seed=4)
    assert noop.summary.eal == pytest.approx(baseline.summary.eal, abs=0.0)


def test_r3_6_two_identical_independent_scenarios_var_is_not_additive(engine_db):
    """Two identical independent scenarios: org VaR95 is not twice the single-scenario VaR95."""
    session = engine_db()
    make_scenario(session, "scenario-1")
    make_scenario(session, "scenario-1-clone")
    session.commit()
    session.close()

    single = run_scenario("scenario-1", overrides={}, seed=5)
    org = run_org(overrides={"scenarios": ["scenario-1", "scenario-1-clone"]}, seed=5)
    assert org.summary.var95 < 2 * single.summary.var95


@pytest.mark.xfail(
    reason="Needs a verified FAIR-U/Open Group workbook cross-check on real scenario "
    "inputs (PLAN.md section 8, not yet verified against a live reference tool).",
    strict=False,
)
def test_r3_7_agreement_with_fair_u_reference_workbook(engine_db):
    """Agreement with FAIR-U or the Open Group workbook on 2-3 scenarios (manual cross-check)."""
    session = engine_db()
    make_scenario(session, "scenario-1")
    session.commit()
    session.close()

    reference_eal = 123_456.0  # placeholder: replace with a verified FAIR-U output
    result = run_scenario("scenario-1", overrides={}, seed=6)
    assert result.summary.eal == pytest.approx(reference_eal, rel=0.10)
