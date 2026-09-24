"""Interface contracts, fixed in build-spec.md section 2.2.

Thin public wrappers: the dataclasses live here (so risk_contract.py can
import them back without a circular import), and each function delegates to
its real implementation in monte_carlo.py / risk_contract.py. Downstream
code (API routers, dashboard pages, tests) should import from this module,
not from the implementation modules directly -- this is the stable contract
build-spec.md section 2.2 asks the whole project to agree on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SummaryResult:
    eal: float
    var95: float
    var99: float
    std_err: float
    lec_points: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class RunResult:
    scenario_id: str | None
    run_id: str
    seed: int
    n_iter: int
    inputs_hash: str
    engine_version: str
    summary: SummaryResult
    loss_vector: np.ndarray


@dataclass
class OrgResult:
    run_id: str
    seed: int
    n_iter: int
    summary: SummaryResult
    loss_vector: np.ndarray
    scenario_results: dict[str, RunResult]


def simulate(inputs: dict, seed: int, n_iter: int) -> np.ndarray:
    """Event-level Monte Carlo per the Risk Contract (build-spec.md section 1.4)."""
    from app.engine.monte_carlo import simulate as _simulate

    return _simulate(inputs, seed, n_iter)


def summarize(loss_vector: np.ndarray) -> SummaryResult:
    """EAL = mean; VaR95/VaR99 = percentiles of the same vector; LEC = 1 - empirical CDF."""
    from app.engine.monte_carlo import summarize as _summarize

    return _summarize(loss_vector)


def run_scenario(scenario_id: str, overrides: dict, seed: int) -> RunResult:
    """Reads the DB, applies the full Risk Contract for one scenario."""
    from app.engine.risk_contract import run_scenario_impl

    return run_scenario_impl(scenario_id, overrides, seed)


def run_org(overrides: dict, seed: int) -> OrgResult:
    """Sums scenario loss vectors iteration-by-iteration. Never sum VaR directly (risk R3)."""
    from app.engine.risk_contract import run_org_impl

    return run_org_impl(overrides, seed)


def attribute(run_id: str, method: str = "allocation") -> list[dict]:
    """Allocates scenario EAL downward to assets/vulns/control-gaps. Returns entity/eal_share rows."""
    from app.engine.risk_contract import attribute_impl

    return attribute_impl(run_id, method)


def apply_controls(scenario_id: str, control_overrides: dict, seed: int) -> RunResult:
    """Mutates control state/effects in memory and reruns with the SAME random draws
    (common random numbers), so ΔEAL isn't buried in Monte Carlo noise (risk R3)."""
    from app.engine.risk_contract import apply_controls_impl

    return apply_controls_impl(scenario_id, control_overrides, seed)
