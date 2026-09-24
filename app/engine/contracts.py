"""Interface contracts, fixed in build-spec.md section 2.2.

Stubs only (PLAN.md Task 2/3). Every function raises NotImplementedError so
the guardrail tests in tests/test_engine_guardrails.py fail loudly against
the stub, proving they are real assertions and not tautologies, before any
implementation lands (CLAUDE.md: "tests before dependents build on a
function").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

ENGINE_VERSION = "0.0.0-stub"


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
    """Event-level Monte Carlo per the Risk Contract (build-spec.md section 1.4).

    Per iteration: draw N ~ Poisson(TEF x Vuln'); for each of the N events,
    draw a primary loss (lognormal) and, with probability SLEF, add a
    secondary loss; sum and truncate at the documented tail cap.
    Returns the annual-loss vector (length n_iter).
    """
    raise NotImplementedError("Task 3: implement event-level Monte Carlo simulate()")


def summarize(loss_vector: np.ndarray) -> SummaryResult:
    """EAL = mean; VaR95/VaR99 = percentiles of the same vector; LEC = 1 - empirical CDF."""
    raise NotImplementedError("Task 3: implement summarize()")


def run_scenario(scenario_id: str, overrides: dict, seed: int) -> RunResult:
    """Reads the DB, applies the full Risk Contract for one scenario."""
    raise NotImplementedError("Task 3: implement run_scenario()")


def run_org(overrides: dict, seed: int) -> OrgResult:
    """Sums scenario loss vectors iteration-by-iteration. Never sum VaR directly (risk R3)."""
    raise NotImplementedError("Task 4: implement run_org()")


def attribute(run_id: str, method: str = "allocation") -> list[dict]:
    """Allocates scenario EAL downward to assets/vulns/control-gaps. Returns entity/eal_share rows."""
    raise NotImplementedError("Task 4: implement attribute()")


def apply_controls(scenario_id: str, control_overrides: dict, seed: int) -> RunResult:
    """Mutates control state/effects in memory and reruns with the SAME random draws
    (common random numbers), so ΔEAL isn't buried in Monte Carlo noise (risk R3)."""
    raise NotImplementedError("Task 7: implement apply_controls()")
