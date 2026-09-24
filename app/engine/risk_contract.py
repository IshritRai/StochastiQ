"""Reads the DB and applies the Risk Contract.

L1 scope note (documented simplification, per the project's L1-then-L2
ladder): control efficacy is applied at its PERT *mode* value
deterministically here, scaling the whole baseline factor range by one
multiplier. Sampling efficacy stochastically per iteration (a true step-3
Monte Carlo draw) is deferred to L2 alongside the tornado/sensitivity
chart, which is where that uncertainty becomes visible anyway. Exposure
adjustment (step 2, telemetry-driven ExposureMult) is also L2 and is an
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
from app.engine.exposure import compute_exposure_mult
from app.engine.monte_carlo import simulate, summarize

ENGINE_VERSION = "0.1.0"

# Factors carried as PERT (low, mode, high) ranges vs. as (p05, p95) magnitude ranges.
_PERT_FACTORS = ("TEF", "Vuln", "SLEF")
_MAGNITUDE_FACTORS = ("PLM", "SLM")

# O-RA control categories -> which top-level factor each category scales
# (avoidance/deterrent are folded into TEF since this engine estimates TEF
# directly rather than decomposing into CF x PoA, per O-RA's "estimate
# factors at the highest level" guidance).
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


def clip_exposure_mult(exposure_mult: float) -> float:
    return float(np.clip(exposure_mult, settings.exposure_mult_lo, settings.exposure_mult_hi))


def _apply_exposure_mult(ranges: dict, exposure_mult: float) -> dict:
    """Step 2 of the Risk Contract. exposure_mult is telemetry-driven
    (app.engine.exposure.compute_exposure_mult), computed from currently-open
    findings unless the caller overrides it explicitly (e.g. What-if/NLQ
    what-if-delay). Either way it is clipped here to
    [exposure_mult_lo, exposure_mult_hi]: THE ONE PLACE this bound is
    enforced (one extreme finding must never swing EAL past a plausible
    range). Callers needing the clipped value for provenance should call
    `clip_exposure_mult` themselves before this."""
    if exposure_mult == 1.0 or "Vuln" not in ranges:
        return ranges
    exposure_mult = clip_exposure_mult(exposure_mult)
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
    from each other (they are modeled as independent risks: "adding
    independent per-scenario vectors understates the tail if risks are
    correlated... state the L1 assumption"; the assumption here is
    independence, so the draws themselves must actually be independent,
    not accidentally identical). Still fully reproducible: the same
    (seed, scenario_id) pair always derives the same effective seed.
    """
    digest = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) % (2**31)


def _hash_inputs(inputs: dict, seed: int, n_iter: int) -> str:
    payload = json.dumps({"inputs": inputs, "seed": seed, "n_iter": n_iter}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _default_tail_cap(session, scenario: m.ThreatScenario) -> float | None:
    """Cap a single event's loss at one year of revenue for the scenario's most
    exposed linked business service (documented assumption), or None if
    the scenario has no linked services yet."""
    services = session.query(m.BusinessService).all()
    if not services:
        return None
    max_revenue_per_hour = max(s.revenue_per_hour for s in services)
    return max_revenue_per_hour * 8760.0


def _sensitivity_tornado(inputs: dict, seed: int, n_iter: int, pct: float | None = None) -> list[dict]:
    """Tornado/sensitivity chart data: perturbs each Risk Contract factor
    by +-pct (default settings.tornado_perturbation_pct) one at a time,
    using the SAME seed for every perturbation (common random numbers),
    and records the resulting EAL swing. Sorted widest-swing-first, as a
    tornado chart expects."""
    pct = pct if pct is not None else settings.tornado_perturbation_pct

    factor_groups: dict[str, list[str]] = {}
    for key in inputs:
        if key == "tail_cap":
            continue
        if isinstance(inputs[key], dict):
            factor_groups[key] = [key]
        else:
            prefix = key.rsplit("_", 1)[0]
            factor_groups.setdefault(prefix, []).append(key)

    results = []
    for factor, keys in factor_groups.items():
        low_inputs = dict(inputs)
        high_inputs = dict(inputs)
        for key in keys:
            value = inputs[key]
            if isinstance(value, dict):
                low_inputs[key] = {k: v * (1 - pct) for k, v in value.items()}
                high_inputs[key] = {k: v * (1 + pct) for k, v in value.items()}
            else:
                low_inputs[key] = value * (1 - pct)
                high_inputs[key] = value * (1 + pct)

        low_eal = summarize(simulate(low_inputs, seed=seed, n_iter=n_iter)).eal
        high_eal = summarize(simulate(high_inputs, seed=seed, n_iter=n_iter)).eal
        results.append(
            {
                "factor": factor,
                "eal_at_low": min(low_eal, high_eal),
                "eal_at_high": max(low_eal, high_eal),
                "swing": abs(high_eal - low_eal),
            }
        )

    results.sort(key=lambda r: r["swing"], reverse=True)
    return results


def _stability_flags(summary, tornado: list[dict]) -> dict:
    """Fragile/Unstable flags.

    Fragile: the single most sensitive factor's tornado swing exceeds
    `fragile_swing_threshold` of EAL, i.e. this scenario's EAL hinges
    heavily on one factor's exact value.
    Unstable: the Monte Carlo standard error is more than
    `unstable_stderr_threshold` of EAL: more iterations are needed before
    this EAL should be trusted to the precision it's displayed at.
    """
    eal = summary.eal
    max_swing = tornado[0]["swing"] if tornado else 0.0
    max_swing_pct = (max_swing / eal) if eal > 0 else 0.0
    stderr_pct = (summary.std_err / eal) if eal > 0 else 0.0
    return {
        "fragile": max_swing_pct > settings.fragile_swing_threshold,
        "unstable": stderr_pct > settings.unstable_stderr_threshold,
        "max_tornado_swing_pct": max_swing_pct,
        "std_err_pct": stderr_pct,
        "most_sensitive_factor": tornado[0]["factor"] if tornado else None,
    }


def run_scenario_impl(scenario_id: str, overrides: dict, seed: int, persist: bool = True):
    """Runs one scenario. `seed` is the caller-facing seed (e.g. the org-level
    seed, or the seed a user typed into the What-if page); the actual draws
    use `_derive_seed(seed, scenario_id)` so that:
      (a) run_scenario(sid, ..., seed=S) and run_org(..., seed=S), which
          internally calls this same function for scenario `sid` with the
          SAME seed=S, always produce byte-identical results for that
          scenario (this is the ONE shared seeding function both paths use;
          do not derive a seed anywhere else), and
      (b) two different scenarios under the same org-level seed still draw
          INDEPENDENT random numbers from each other.
    """
    from app.engine.contracts import RunResult  # local import: avoid circular import

    overrides = overrides or {}
    n_iter = overrides.get("n_iter", settings.default_n_iter)
    control_state_overrides = overrides.get("control_state_overrides")
    effective_seed = _derive_seed(seed, scenario_id)

    with session_scope() as session:
        scenario = session.get(m.ThreatScenario, scenario_id)
        if scenario is None:
            raise ValueError(f"Unknown scenario_id: {scenario_id!r}")

        if "exposure_mult" in overrides:
            exposure_mult = overrides["exposure_mult"]
            exposure_breakdown = None
        else:
            # Task 15: telemetry-driven, computed from currently-open
            # findings rather than defaulting to the L1 identity 1.0. The
            # hard R1 bound is enforced in _apply_exposure_mult below.
            exposure_breakdown = compute_exposure_mult(session)
            exposure_mult = exposure_breakdown.exposure_mult_raw

        ranges = _load_scenario_input_ranges(session, scenario_id)
        multipliers = _scenario_control_multipliers(session, scenario_id, control_state_overrides)
        ranges = _apply_multipliers(ranges, multipliers)
        ranges = _apply_exposure_mult(ranges, exposure_mult)
        inputs = _ranges_to_simulate_inputs(ranges)

        tail_cap = overrides.get("tail_cap", _default_tail_cap(session, scenario))
        if tail_cap is not None:
            inputs["tail_cap"] = tail_cap

        loss_vector = simulate(inputs, seed=effective_seed, n_iter=n_iter)
        summary = summarize(loss_vector)
        inputs_hash = _hash_inputs(inputs, effective_seed, n_iter)
        run_id = str(uuid.uuid4())

        clipped_exposure_mult = clip_exposure_mult(exposure_mult) if "Vuln" in ranges else 1.0
        exposure_mult_was_clipped = clipped_exposure_mult != exposure_mult

        tornado = _sensitivity_tornado(inputs, effective_seed, n_iter)
        stability = _stability_flags(summary, tornado)
        stability["tornado"] = tornado

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
        exposure_mult=clipped_exposure_mult,
        exposure_mult_clipped=exposure_mult_was_clipped,
        exposure_breakdown=exposure_breakdown.__dict__ if exposure_breakdown is not None else None,
        stability=stability,
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
    # Pass the SAME org-level seed to every scenario; run_scenario_impl is the
    # one place that derives the effective per-scenario seed (see its
    # docstring), so this equals run_scenario(sid, ..., seed=seed) exactly.
    scenario_results = {
        sid: run_scenario_impl(sid, scenario_overrides, seed=seed, persist=False)
        for sid in scenario_ids
    }

    n_iter = next(iter(scenario_results.values())).n_iter
    # Sum loss vectors iteration-by-iteration, NEVER sum VaR across scenarios
    # ("VaR is not additive").
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
    leave-one-out is L2."""
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
    delta-EAL exactly 0."""
    overrides = {"control_state_overrides": control_overrides} if control_overrides else {}
    return run_scenario_impl(scenario_id, overrides, seed=seed, persist=persist)
