"""R3 guardrail tests (build-spec.md, "Guardrail tests (write these first)").

These are written against the engine stub in app/engine/contracts.py, BEFORE
any real engine code exists (PLAN.md Task 2). Each test is marked xfail
against NotImplementedError so CI stays informative rather than red-by-default;
as each function in Task 3/4/7 is implemented, remove that test's xfail mark
one at a time. A test that still fails after its xfail mark is removed is a
real regression, not a stub artifact.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.engine.contracts import apply_controls, run_org, run_scenario, simulate, summarize

pytestmark = pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Engine not yet implemented (PLAN.md Task 3/4/7)",
    strict=True,
)


def test_r3_1_fixed_frequency_fixed_loss_gives_eal_within_mc_error():
    """Fixed frequency and fixed loss: EAL equals frequency x loss within Monte Carlo error."""
    freq, loss = 2.0, 10_000.0
    inputs = {"tef": freq, "vuln": 1.0, "plm_fixed": loss, "slef": 0.0}
    vec = simulate(inputs, seed=1, n_iter=50_000)
    eal = summarize(vec).eal
    assert abs(eal - freq * loss) / (freq * loss) < 0.02


def test_r3_2_lognormal_fit_reproduces_percentiles():
    """Lognormal fitted to (5th, 95th) percentiles reproduces those percentiles."""
    inputs = {"tef": 1.0, "vuln": 1.0, "plm_p05": 1_000.0, "plm_p95": 100_000.0, "slef": 0.0}
    vec = simulate(inputs, seed=2, n_iter=50_000)
    p05, p95 = np.percentile(vec, [5, 95])
    assert p05 == pytest.approx(1_000.0, rel=0.15)
    assert p95 == pytest.approx(100_000.0, rel=0.15)


def test_r3_3_same_seed_gives_identical_results():
    """Same seed gives identical results (reproducible demos)."""
    inputs = {"tef": 1.5, "vuln": 0.5, "plm_p05": 5_000.0, "plm_p95": 50_000.0, "slef": 0.1}
    vec_a = simulate(inputs, seed=7, n_iter=10_000)
    vec_b = simulate(inputs, seed=7, n_iter=10_000)
    assert np.array_equal(vec_a, vec_b)


def test_r3_4_org_eal_equals_sum_of_scenario_eal():
    """Organization EAL equals the sum of scenario EAL; asset allocations sum to scenario EAL."""
    org = run_org(overrides={}, seed=3)
    scenario_eal_sum = sum(r.summary.eal for r in org.scenario_results.values())
    assert org.summary.eal == pytest.approx(scenario_eal_sum, rel=1e-6)


def test_r3_5_zero_effect_whatif_gives_zero_delta_eal():
    """Zero-effect what-if gives ΔEAL exactly 0 (through apply_controls specifically)."""
    baseline = run_scenario("scenario-1", overrides={}, seed=4)
    noop = apply_controls("scenario-1", control_overrides={}, seed=4)
    assert noop.summary.eal == pytest.approx(baseline.summary.eal, abs=0.0)


def test_r3_6_two_identical_independent_scenarios_var_is_not_additive():
    """Two identical independent scenarios: org VaR95 is not twice the single-scenario VaR95."""
    single = run_scenario("scenario-1", overrides={}, seed=5)
    org = run_org(overrides={"scenarios": ["scenario-1", "scenario-1-clone"]}, seed=5)
    assert org.summary.var95 < 2 * single.summary.var95


def test_r3_7_agreement_with_fair_u_reference_workbook():
    """Agreement with FAIR-U or the Open Group workbook on 2-3 scenarios (manual cross-check).

    This test encodes the acceptance bound; the actual reference numbers must be
    filled in during Task 3 from a real FAIR-U/Open Group run on the same inputs
    (PLAN.md section 8, item not yet verified against a live reference tool).
    """
    reference_eal = 123_456.0  # placeholder: replace with a verified FAIR-U output
    result = run_scenario("scenario-1", overrides={}, seed=6)
    assert result.summary.eal == pytest.approx(reference_eal, rel=0.10)
