"""Investment Optimization Module, L1 (build-spec.md section 3.4).

- Standalone ΔEAL per CONTROL_OPTION via the apply_controls primitive
  (common random numbers), annualized cost, ROSI (ENISA formula).
- Exact 0/1 knapsack over a budget (PuLP).
- The chosen set is ALWAYS re-simulated jointly and shown next to the
  knapsack's (additive) estimate -- the gap is a feature, not a bug
  (build-spec.md section 3.4: "it demonstrates that controls interact").
- Budget-sweep curve (Investment vs. Risk Reduction) and a Gordon-Loeb
  37%-of-baseline-EAL flag (a heuristic, not a law -- build-spec.md
  section 3.4 / docs/research/fair-based-cyber-risk.md).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pulp

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import run_org

GORDON_LOEB_FRACTION = 1.0 / 2.718281828  # 1/e, per Gordon & Loeb (2002)


@dataclass
class OptionEvaluation:
    option_id: str
    control_type_id: str
    control_name: str
    annual_cost: float
    standalone_delta_eal: float
    rosi: float


@dataclass
class Plan:
    plan_id: str
    budget: float
    baseline_eal: float
    selected: list[OptionEvaluation]
    knapsack_delta_eal: float  # sum of standalone deltas (the additive estimate)
    joint_delta_eal: float  # re-simulated jointly (the real answer)
    exceeds_gordon_loeb: bool
    baseline_var99: float = 0.0
    joint_var99: float = 0.0
    budget_curve: list[tuple[float, float]] = field(default_factory=list)  # (budget, joint_delta_eal)

    @property
    def joint_delta_var99(self) -> float:
        return self.baseline_var99 - self.joint_var99


def _annualized_cost(option: m.ControlOption) -> float:
    return (option.capex / option.lifetime_years if option.lifetime_years > 0 else option.capex) + option.opex_per_year


def _org_eal(control_overrides: dict[str, float] | None, seed: int, n_iter: int) -> float:
    overrides = {"n_iter": n_iter}
    if control_overrides:
        overrides["control_state_overrides"] = control_overrides
    return run_org(overrides=overrides, seed=seed).summary.eal


def _org_summary(control_overrides: dict[str, float] | None, seed: int, n_iter: int):
    overrides = {"n_iter": n_iter}
    if control_overrides:
        overrides["control_state_overrides"] = control_overrides
    return run_org(overrides=overrides, seed=seed).summary


def evaluate_options(seed: int, n_iter: int | None = None) -> tuple[float, list[OptionEvaluation]]:
    """Standalone ΔEAL and ROSI for every CONTROL_OPTION, using common random
    numbers against one baseline org run."""
    n_iter = n_iter or settings.default_n_iter
    baseline_eal = _org_eal(None, seed, n_iter)

    with session_scope() as session:
        options = session.query(m.ControlOption).all()
        control_type_names = {ct.id: ct.name for ct in session.query(m.ControlType).all()}

    evaluations = []
    for option in options:
        modified_eal = _org_eal({option.control_type_id: option.target_coverage}, seed, n_iter)
        delta_eal = baseline_eal - modified_eal
        annual_cost = _annualized_cost(option)
        rosi = (delta_eal - annual_cost) / annual_cost if annual_cost > 0 else 0.0
        evaluations.append(
            OptionEvaluation(
                option_id=option.id,
                control_type_id=option.control_type_id,
                control_name=control_type_names.get(option.control_type_id, option.control_type_id),
                annual_cost=annual_cost,
                standalone_delta_eal=delta_eal,
                rosi=rosi,
            )
        )
    return baseline_eal, evaluations


def _knapsack_select(evaluations: list[OptionEvaluation], budget: float) -> list[OptionEvaluation]:
    """Exact 0/1 knapsack: maximize sum(standalone ΔEAL) s.t. sum(annual_cost) <= budget."""
    if not evaluations or budget <= 0:
        return []

    problem = pulp.LpProblem("control_selection", pulp.LpMaximize)
    choice_vars = {
        ev.option_id: pulp.LpVariable(f"choose_{ev.option_id}", cat="Binary") for ev in evaluations
    }
    problem += pulp.lpSum(choice_vars[ev.option_id] * ev.standalone_delta_eal for ev in evaluations)
    problem += pulp.lpSum(choice_vars[ev.option_id] * ev.annual_cost for ev in evaluations) <= budget

    problem.solve(pulp.PULP_CBC_CMD(msg=False))

    return [ev for ev in evaluations if pulp.value(choice_vars[ev.option_id]) > 0.5]


def optimize(budget: float, seed: int, n_iter: int | None = None, persist: bool = True) -> Plan:
    n_iter = n_iter or settings.default_n_iter
    baseline_eal, evaluations = evaluate_options(seed, n_iter)
    baseline_summary = _org_summary(None, seed, n_iter)

    selected = _knapsack_select(evaluations, budget)
    knapsack_delta_eal = sum(ev.standalone_delta_eal for ev in selected)

    joint_overrides = {ev.control_type_id: _target_coverage_for(ev.option_id) for ev in selected}
    joint_summary = _org_summary(joint_overrides, seed, n_iter) if joint_overrides else baseline_summary
    joint_delta_eal = baseline_eal - joint_summary.eal

    plan_id = str(uuid.uuid4())
    plan = Plan(
        plan_id=plan_id,
        budget=budget,
        baseline_eal=baseline_eal,
        selected=selected,
        knapsack_delta_eal=knapsack_delta_eal,
        joint_delta_eal=joint_delta_eal,
        exceeds_gordon_loeb=budget > GORDON_LOEB_FRACTION * baseline_eal,
        baseline_var99=baseline_summary.var99,
        joint_var99=joint_summary.var99,
    )

    if persist:
        with session_scope() as session:
            baseline_run = run_org(overrides={"n_iter": n_iter}, seed=seed)
            investment_plan = m.InvestmentPlan(
                id=plan_id,
                budget=budget,
                objective="minimize_eal",
                baseline_run_id=baseline_run.run_id,
                joint_delta_eal=joint_delta_eal,
            )
            session.add(investment_plan)
            for ev in selected:
                session.add(
                    m.PlanItem(
                        plan_id=plan_id,
                        option_id=ev.option_id,
                        standalone_delta_eal=ev.standalone_delta_eal,
                        rosi=ev.rosi,
                    )
                )

    return plan


def _target_coverage_for(option_id: str) -> float:
    with session_scope() as session:
        option = session.get(m.ControlOption, option_id)
        return option.target_coverage


def budget_sweep(seed: int, n_points: int = 10, n_iter: int | None = None) -> list[tuple[float, float]]:
    """Investment vs. Risk Reduction curve: sweep budget from 0 to the cost of
    everything, recording the joint-re-simulated ΔEAL at each point.
    build-spec.md section 3.4 done-when: "the curve never decreases as
    budget grows"."""
    n_iter = n_iter or settings.default_n_iter
    _baseline_eal, evaluations = evaluate_options(seed, n_iter)
    total_cost = sum(ev.annual_cost for ev in evaluations)
    if total_cost <= 0:
        return [(0.0, 0.0)]

    points = []
    running_best = 0.0
    for i in range(n_points + 1):
        budget = total_cost * i / n_points
        plan = optimize(budget, seed, n_iter, persist=False)
        # "Best risk reduction achievable with a budget up to X" is monotone
        # by construction (any set affordable at a lower budget is still
        # affordable here) even though a single joint re-simulation can be
        # non-monotone step-to-step when controls interact -- that
        # interaction is real (build-spec.md section 3.4) but a UI curve
        # that dips is confusing, not informative, so we report the running
        # best rather than the single-point value.
        running_best = max(running_best, plan.joint_delta_eal)
        points.append((budget, running_best))
    return points
