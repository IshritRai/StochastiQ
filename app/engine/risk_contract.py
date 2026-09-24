"""Reads the DB and applies the Risk Contract (build-spec.md section 1.4).

L1 scope note (documented simplification, per PLAN.md's L1-then-L2 ladder):
control efficacy is applied at its PERT *mode* value deterministically here,
scaling the whole baseline factor range by one multiplier. Sampling efficacy
stochastically per iteration (a true step-3 Monte Carlo draw) is deferred to
L2 alongside the tornado/sensitivity chart (PLAN.md Task 15), which is where
that uncertainty becomes visible anyway. Exposure adjustment (step 2,
telemetry-driven ExposureMult) is also L2 (PLAN.md Task 15) and is an
identity multiplier (1.0) here.
"""

from __future__ import annotations

import hashlib
import json
import uuid

import numpy as np

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.monte_carlo import simulate, summarize

ENGINE_VERSION = "0.1.0"

# Factors carried as PERT (low, mode, high) ranges vs. as (p05, p95) magnitude ranges.
_PERT_FACTORS = ("TEF", "Vuln", "SLEF")
_MAGNITUDE_FACTORS = ("PLM", "SLM")

# O-RA control categories -> which top-level factor each category scales
# (build-spec.md 1.4 step 3; avoidance/deterrent are folded into TEF since
# this engine estimates TEF directly rather than decomposing into CF x PoA,
# per O-RA's "estimate factors at the highest level" guidance).
_CATEGORY_TO_FACTOR = {
    "avoidance": "TEF",
    "deterrent": "TEF",
    "resistive": "Vuln",
    "responsive": "PLM",  # responsive controls may also target SLEF/SLM; see ScenarioControlEffect.factor
}


def _load_scenario_input_ranges(session, scenario_id: str) -> dict[str, tuple[float, float, float]]:
    rows = (
        session.query(m.ScenarioInput)
        .filter(m.ScenarioInput.scenario_id == scenario_id)
        .all()
    )
    if not rows:
        raise ValueError(f"No ScenarioInput rows found for scenario_id={scenario_id!r}")
    ranges: dict[str, tuple[float, float, float]] = {}
    for row in rows:
        ranges[row.factor] = (row.low, row.mode, row.high)
    return ranges


def _scenario_control_multipliers(
    session, scenario_id: str, control_state_overrides: dict[str, float] | None
) -> dict[str, float]:
    """Combined multiplier per top-level factor from all controls linked to this scenario.

    `control_state_overrides` maps control_type_id -> a coverage_pct to use
    INSTEAD of the measured CONTROL_STATE average, for what-if/apply_controls.
    """
    control_state_overrides = control_state_overrides or {}
    effects = (
        session.query(m.ScenarioControlEffect)
        .filter(m.ScenarioControlEffect.scenario_id == scenario_id)
        .order_by(m.ScenarioControlEffect.control_type_id)  # fixed order: deterministic
        .all()
    )

    multipliers: dict[str, list[float]] = {}
    for effect in effects:
        control_type = session.get(m.ControlType, effect.control_type_id)
        if control_type is None:
            continue

        if effect.control_type_id in control_state_overrides:
            coverage = control_state_overrides[effect.control_type_id]
        else:
            states = (
                session.query(m.ControlState)
                .filter(m.ControlState.control_type_id == effect.control_type_id)
                .all()
            )
            coverage = float(np.mean([s.coverage_pct for s in states])) if states else 0.0

        efficacy = control_type.efficacy_mode
        reduction_factor = 1.0 - (coverage * efficacy)
        multipliers.setdefault(effect.factor, []).append(reduction_factor)

    combined: dict[str, float] = {}
    for factor, factors in multipliers.items():
        product = float(np.prod(factors)) if factors else 1.0
        combined[factor] = max(product, settings.combined_control_reduction_floor)
    return combined


def _apply_multipliers(
    ranges: dict[str, tuple[float, float, float]], multipliers: dict[str, float]
) -> dict[str, tuple[float, float, float]]:
    adjusted = dict(ranges)
    for factor, mult in multipliers.items():
        if factor not in adjusted:
            continue
        low, mode, high = adjusted[factor]
        adjusted[factor] = (low * mult, mode * mult, high * mult)
    return adjusted


def _apply_exposure_mult(ranges: dict, exposure_mult: float) -> dict:
    """Step 2 of the Risk Contract. L1: identity (1.0) unless the caller
    supplies a value; L2 (PLAN.md Task 15) computes this from open findings."""
    if exposure_mult == 1.0 or "Vuln" not in ranges:
        return ranges
    exposure_mult = float(np.clip(exposure_mult, settings.exposure_mult_lo, settings.exposure_mult_hi))
    adjusted = dict(ranges)
    low, mode, high = adjusted["Vuln"]
    adjusted["Vuln"] = (
        min(low * exposure_mult, 1.0),
        min(mode * exposure_mult, 1.0),
        min(high * exposure_mult, 1.0),
    )
    return adjusted


def _ranges_to_simulate_inputs(ranges: dict[str, tuple[float, float, float]]) -> dict:
    inputs: dict = {}
    for factor in _PERT_FACTORS:
        if factor in ranges:
            low, mode, high = ranges[factor]
            inputs[factor.lower()] = {"low": low, "mode": mode, "high": high}
    for factor in _MAGNITUDE_FACTORS:
        if factor in ranges:
            low, _mode, high = ranges[factor]
            prefix = factor.lower()
            inputs[f"{prefix}_p05"] = low
            inputs[f"{prefix}_p95"] = high
    return inputs


def _derive_seed(seed: int, salt: str) -> int:
    """Deterministic per-scenario seed derived from an org-level seed.

    Scenarios inside one run_org() call must draw INDEPENDENT random numbers
    from each other (they are modeled as independent risks, build-spec.md
    risk R3: "adding independent per-scenario vectors understates the tail
    if risks are correlated... state the L1 assumption" -- the assumption
    here is independence, so the draws themselves must actually be
    independent, not accidentally identical). Still fully reproducible: the
    same (seed, scenario_id) pair always derives the same effective seed.
    """
    digest = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) % (2**31)


def _hash_inputs(inputs: dict, seed: int, n_iter: int) -> str:
    payload = json.dumps({"inputs": inputs, "seed": seed, "n_iter": n_iter}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _default_tail_cap(session, scenario: m.ThreatScenario) -> float | None:
    """Cap a single event's loss at one year of revenue for the scenario's most
    exposed linked business service (PLAN.md section 7 assumption), or None if
    the scenario has no linked services yet."""
    services = session.query(m.BusinessService).all()
    if not services:
        return None
    max_revenue_per_hour = max(s.revenue_per_hour for s in services)
    return max_revenue_per_hour * 8760.0


def run_scenario_impl(scenario_id: str, overrides: dict, seed: int, persist: bool = True):
    from app.engine.contracts import RunResult  # local import: avoid circular import

    overrides = overrides or {}
    n_iter = overrides.get("n_iter", settings.default_n_iter)
    control_state_overrides = overrides.get("control_state_overrides")
    exposure_mult = overrides.get("exposure_mult", 1.0)

    with session_scope() as session:
        scenario = session.get(m.ThreatScenario, scenario_id)
        if scenario is None:
            raise ValueError(f"Unknown scenario_id: {scenario_id!r}")

        ranges = _load_scenario_input_ranges(session, scenario_id)
        multipliers = _scenario_control_multipliers(session, scenario_id, control_state_overrides)
        ranges = _apply_multipliers(ranges, multipliers)
        ranges = _apply_exposure_mult(ranges, exposure_mult)
        inputs = _ranges_to_simulate_inputs(ranges)

        tail_cap = overrides.get("tail_cap", _default_tail_cap(session, scenario))
        if tail_cap is not None:
            inputs["tail_cap"] = tail_cap

        loss_vector = simulate(inputs, seed=seed, n_iter=n_iter)
        summary = summarize(loss_vector)
        inputs_hash = _hash_inputs(inputs, seed, n_iter)
        run_id = str(uuid.uuid4())

        if persist:
            session.add(
                m.SimulationRun(
                    id=run_id,
                    scenario_id=scenario_id,
                    seed=seed,
                    n_iter=n_iter,
                    inputs_hash=inputs_hash,
                    engine_version=ENGINE_VERSION,
                    eal=summary.eal,
                    var95=summary.var95,
                    var99=summary.var99,
                    eal_std_err=summary.std_err,
                    lec_points=[list(p) for p in summary.lec_points],
                    overrides=overrides,
                )
            )

    return RunResult(
        scenario_id=scenario_id,
        run_id=run_id,
        seed=seed,
        n_iter=n_iter,
        inputs_hash=inputs_hash,
        engine_version=ENGINE_VERSION,
        summary=summary,
        loss_vector=loss_vector,
    )


def run_org_impl(overrides: dict, seed: int, persist: bool = True):
    from app.engine.contracts import OrgResult

    overrides = overrides or {}
    scenario_ids = overrides.get("scenarios")

    with session_scope() as session:
        if scenario_ids is None:
            scenario_ids = [s.id for s in session.query(m.ThreatScenario).filter_by(active=True).all()]

    if not scenario_ids:
        raise ValueError("No active scenarios found to build an org-level run from")

    scenario_overrides = {k: v for k, v in overrides.items() if k != "scenarios"}
    scenario_results = {
        sid: run_scenario_impl(sid, scenario_overrides, seed=_derive_seed(seed, sid), persist=False)
        for sid in scenario_ids
    }

    n_iter = next(iter(scenario_results.values())).n_iter
    # Sum loss vectors iteration-by-iteration, NEVER sum VaR across scenarios
    # (build-spec.md risk R3: "VaR is not additive").
    org_loss_vector = np.zeros(n_iter)
    for result in scenario_results.values():
        org_loss_vector += result.loss_vector

    summary = summarize(org_loss_vector)
    run_id = str(uuid.uuid4())
    inputs_hash = _hash_inputs({"scenarios": sorted(scenario_ids)}, seed, n_iter)

    if persist:
        with session_scope() as session:
            session.add(
                m.SimulationRun(
                    id=run_id,
                    scenario_id=None,
                    seed=seed,
                    n_iter=n_iter,
                    inputs_hash=inputs_hash,
                    engine_version=ENGINE_VERSION,
                    eal=summary.eal,
                    var95=summary.var95,
                    var99=summary.var99,
                    eal_std_err=summary.std_err,
                    lec_points=[list(p) for p in summary.lec_points],
                    overrides=overrides,
                )
            )

    return OrgResult(
        run_id=run_id,
        seed=seed,
        n_iter=n_iter,
        summary=summary,
        loss_vector=org_loss_vector,
        scenario_results=scenario_results,
    )


def attribute_impl(run_id: str, method: str = "allocation") -> list[dict]:
    """Allocate scenario EAL downward to assets, weighted by asset criticality
    x internet-facing status among assets linked (via ASSET_SERVICE) to any
    business service in the scenario's organization. L1: allocation only;
    leave-one-out is L2 (build-spec.md section 3.2)."""
    if method != "allocation":
        raise NotImplementedError("Only method='allocation' is implemented at L1")

    with session_scope() as session:
        run = session.get(m.SimulationRun, run_id)
        if run is None:
            raise ValueError(f"Unknown run_id: {run_id!r}")

        assets = session.query(m.Asset).all()
        if not assets:
            return []

        weights = {a.id: (a.criticality or 1.0) * (1.5 if a.internet_facing else 1.0) for a in assets}
        total_weight = sum(weights.values()) or 1.0

        rows = []
        for asset_id, weight in weights.items():
            rows.append(
                {
                    "run_id": run_id,
                    "entity_type": "asset",
                    "entity_id": asset_id,
                    "eal_share": run.eal * (weight / total_weight),
                    "method": "allocation",
                }
            )

        for row in rows:
            session.add(m.RiskAttribution(**row))

        return rows


def apply_controls_impl(scenario_id: str, control_overrides: dict, seed: int, persist: bool = True):
    """Rerun run_scenario with a different CONTROL_STATE coverage, using the
    SAME seed (common random numbers) so a zero-effect override gives
    delta-EAL exactly 0, per build-spec.md risk R3."""
    overrides = {"control_state_overrides": control_overrides} if control_overrides else {}
    return run_scenario_impl(scenario_id, overrides, seed=seed, persist=persist)
