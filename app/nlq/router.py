"""Intent router: 9 intents, each mapped to a real function
(build-spec.md section 3.3, L1). Unsupported questions get an honest
"I can't answer that yet" rather than a guess (build-spec.md risk R5).
"""

from __future__ import annotations

import re

from app.compliance.status import compliance_status
from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import attribute, run_org
from app.nlq.contracts import Answer
from app.optimize.optimizer import optimize
from app.optimize.recommendations import top_finding_recommendations

_SEED = settings.default_seed
_N_ITER = settings.default_n_iter


def _fmt(amount: float) -> str:
    from dashboard.format_utils import format_inr

    return format_inr(amount)


def _handle_org_eal(_question: str) -> Answer:
    org = run_org(overrides={"n_iter": _N_ITER}, seed=_SEED)
    return Answer(
        text=f"The organization's Expected Annual Loss is {_fmt(org.summary.eal)} "
        f"(VaR95: {_fmt(org.summary.var95)}).",
        figures={"eal": org.summary.eal, "var95": org.summary.var95},
        provenance={"run_id": org.run_id, "seed": org.seed, "source": "run_org"},
        intent="org_eal",
    )


def _handle_top_scenarios(_question: str) -> Answer:
    org = run_org(overrides={"n_iter": _N_ITER}, seed=_SEED)
    with session_scope() as session:
        names = {sid: session.get(m.ThreatScenario, sid).name for sid in org.scenario_results}
    ranked = sorted(org.scenario_results.items(), key=lambda kv: -kv[1].summary.eal)[:3]
    lines = [f"{names[sid]}: {_fmt(r.summary.eal)}" for sid, r in ranked]
    return Answer(
        text="Top scenarios by Expected Annual Loss: " + "; ".join(lines) + ".",
        figures={names[sid]: r.summary.eal for sid, r in ranked},
        provenance={"run_id": org.run_id, "seed": org.seed, "source": "run_org"},
        intent="top_scenarios",
    )


def _handle_highest_risk(_question: str) -> Answer:
    org = run_org(overrides={"n_iter": _N_ITER}, seed=_SEED)
    rows = attribute(org.run_id)
    if not rows:
        return Answer(
            text="No risk attribution is available yet.",
            provenance={"run_id": org.run_id, "source": "attribute"},
            intent="highest_risk",
        )
    top = max(rows, key=lambda r: r["eal_share"])
    with session_scope() as session:
        asset = session.get(m.Asset, top["entity_id"])
    return Answer(
        text=f"The highest single risk contributor is {asset.hostname if asset else top['entity_id']}, "
        f"attributed {_fmt(top['eal_share'])} of Expected Annual Loss.",
        figures={"eal_share": top["eal_share"]},
        provenance={"run_id": org.run_id, "source": "attribute"},
        intent="highest_risk",
    )


def _handle_top_vulnerabilities(_question: str) -> Answer:
    recs = top_finding_recommendations(limit=5)
    if not recs:
        return Answer(
            text="No open findings are driving loss right now.",
            provenance={"source": "top_finding_recommendations"},
            intent="top_vulnerabilities",
        )
    lines = [f"{r.rule_or_cve} on {r.asset_hostname} (risk score {r.risk_score:.1f})" for r in recs]
    return Answer(
        text="Top findings by risk score (KEV-listed CVEs weighted higher): " + "; ".join(lines) + ".",
        figures={r.rule_or_cve: r.risk_score for r in recs},
        provenance={"source": "top_finding_recommendations"},
        intent="top_vulnerabilities",
    )


def _handle_eal_by_bu(_question: str) -> Answer:
    org = run_org(overrides={"n_iter": _N_ITER}, seed=_SEED)
    rows = attribute(org.run_id)
    with session_scope() as session:
        assets = {a.id: a for a in session.query(m.Asset).all()}
        bus = {b.id: b.name for b in session.query(m.BusinessUnit).all()}

    by_bu: dict[str, float] = {}
    for row in rows:
        asset = assets.get(row["entity_id"])
        if asset is None:
            continue
        bu_name = bus.get(asset.bu_id, asset.bu_id)
        by_bu[bu_name] = by_bu.get(bu_name, 0.0) + row["eal_share"]

    lines = [f"{name}: {_fmt(val)}" for name, val in sorted(by_bu.items(), key=lambda kv: -kv[1])]
    return Answer(
        text="Expected Annual Loss by business unit: " + "; ".join(lines) + ".",
        figures=by_bu,
        provenance={"run_id": org.run_id, "source": "attribute"},
        intent="eal_by_bu",
    )


def _handle_whatif_mfa(_question: str) -> Answer:
    with session_scope() as session:
        mfa_ct = session.query(m.ControlType).filter(m.ControlType.name.ilike("%MFA%")).first()
    if mfa_ct is None:
        return Answer(
            text="No MFA control is configured yet, so I can't run that what-if.",
            provenance={"source": "run_org"},
            intent="whatif_mfa",
        )

    baseline = run_org(overrides={"n_iter": _N_ITER}, seed=_SEED)
    modified = run_org(
        overrides={"n_iter": _N_ITER, "control_state_overrides": {mfa_ct.id: 1.0}}, seed=_SEED
    )
    delta = baseline.summary.eal - modified.summary.eal
    return Answer(
        text=f"If MFA were implemented across all privileged accounts (100% coverage), "
        f"Expected Annual Loss would fall by {_fmt(delta)}, from {_fmt(baseline.summary.eal)} "
        f"to {_fmt(modified.summary.eal)}.",
        figures={"baseline_eal": baseline.summary.eal, "modified_eal": modified.summary.eal, "delta_eal": delta},
        provenance={"baseline_run_id": baseline.run_id, "modified_run_id": modified.run_id, "source": "apply_controls"},
        intent="whatif_mfa",
    )


_DAYS_PATTERN = re.compile(r"(\d+)\s*day")


def _handle_delay_impact(question: str) -> Answer:
    match = _DAYS_PATTERN.search(question)
    n_days = int(match.group(1)) if match else 30

    # Exposure-days model (documented L1 assumption, build-spec.md section 3.3):
    # delaying remediation for a fraction of the year raises the exposure index
    # proportionally to that fraction. Not a simulated finding-level effect --
    # a bounded, labeled approximation until Task 15's telemetry-driven
    # ExposureMult replaces it.
    exposure_mult = 1.0 + (n_days / 365.0)
    baseline = run_org(overrides={"n_iter": _N_ITER}, seed=_SEED)
    delayed = run_org(overrides={"n_iter": _N_ITER, "exposure_mult": exposure_mult}, seed=_SEED)
    delta = delayed.summary.eal - baseline.summary.eal
    return Answer(
        text=f"Delaying remediation by {n_days} days is modeled (exposure-days assumption, "
        f"see build-spec.md section 3.3) as raising Expected Annual Loss by {_fmt(delta)}, "
        f"from {_fmt(baseline.summary.eal)} to {_fmt(delayed.summary.eal)}.",
        figures={"baseline_eal": baseline.summary.eal, "delayed_eal": delayed.summary.eal, "delta_eal": delta, "days": n_days},
        provenance={"baseline_run_id": baseline.run_id, "delayed_run_id": delayed.run_id, "source": "run_org"},
        intent="delay_impact",
    )


_MONEY_PATTERN = re.compile(r"(\d[\d,]*\.?\d*)\s*(crore|cr|lakh|lakhs|l)?", re.IGNORECASE)


def _parse_inr_amount(question: str) -> float | None:
    for match in _MONEY_PATTERN.finditer(question):
        number_str, unit = match.groups()
        if not number_str or number_str in (",",):
            continue
        try:
            number = float(number_str.replace(",", ""))
        except ValueError:
            continue
        if unit and unit.lower() in ("crore", "cr"):
            return number * 1_00_00_000
        if unit and unit.lower() in ("lakh", "lakhs", "l"):
            return number * 1_00_000
        if unit is None and number >= 1000:
            return number
    return None


def _handle_best_plan_for_budget(question: str) -> Answer:
    budget = _parse_inr_amount(question)
    if budget is None:
        return Answer(
            text="I can tell you the best plan for a budget, but I couldn't find an amount "
            "in your question -- try e.g. 'best plan for a budget of 1 crore'.",
            provenance={"source": "optimize"},
            intent="best_plan_for_budget",
        )

    plan = optimize(budget=budget, seed=_SEED, n_iter=_N_ITER)
    with session_scope() as session:
        control_names = {ct.id: ct.name for ct in session.query(m.ControlType).all()}
    selected_names = [control_names.get(ev.control_type_id, ev.control_type_id) for ev in plan.selected]
    return Answer(
        text=f"For a budget of {_fmt(budget)}, the recommended plan is: "
        f"{', '.join(selected_names) if selected_names else '(nothing fits this budget)'}. "
        f"Jointly re-simulated, this reduces Expected Annual Loss by {_fmt(plan.joint_delta_eal)}.",
        figures={"budget": budget, "joint_delta_eal": plan.joint_delta_eal, "knapsack_delta_eal": plan.knapsack_delta_eal},
        provenance={"plan_id": plan.plan_id, "source": "optimize"},
        intent="best_plan_for_budget",
    )


def _handle_compliance_gaps(_question: str) -> Answer:
    with session_scope() as session:
        has_framework = session.query(m.Framework).first() is not None
    if not has_framework:
        return Answer(
            text="No compliance framework is imported yet.",
            provenance={"source": "compliance_status"},
            intent="compliance_gaps",
        )
    rows = compliance_status(framework="NIST CSF", scope="org")
    gaps = [r for r in rows if r["status"] == "gap"]
    if not gaps:
        return Answer(
            text="No compliance gaps found against NIST CSF 2.0 in the current mapping.",
            figures={"n_gaps": 0},
            provenance={"source": "compliance_status"},
            intent="compliance_gaps",
        )
    names = ", ".join(f"{g['control_id']} ({g['short_title']})" for g in gaps[:5])
    return Answer(
        text=f"{len(gaps)} subcategories show a compliance gap. Top ones: {names}.",
        figures={"n_gaps": len(gaps)},
        provenance={"source": "compliance_status"},
        intent="compliance_gaps",
    )


# Ordered: more specific intents first, since "what if MFA" also contains
# risk-adjacent words that a looser pattern might otherwise catch first.
_INTENTS: list[tuple[re.Pattern, callable]] = [
    (re.compile(r"\bmfa\b", re.IGNORECASE), _handle_whatif_mfa),
    (re.compile(r"delay.*(remediation|patch)|(remediation|patch).*delay", re.IGNORECASE), _handle_delay_impact),
    (re.compile(r"budget|invest|plan for", re.IGNORECASE), _handle_best_plan_for_budget),
    (re.compile(r"complian|framework|gap", re.IGNORECASE), _handle_compliance_gaps),
    (re.compile(r"business unit|\bbu\b", re.IGNORECASE), _handle_eal_by_bu),
    (re.compile(r"vulnerabilit|cve|finding", re.IGNORECASE), _handle_top_vulnerabilities),
    (re.compile(r"scenario", re.IGNORECASE), _handle_top_scenarios),
    (re.compile(r"highest.*risk|biggest risk|top risk|riskiest", re.IGNORECASE), _handle_highest_risk),
    (
        re.compile(r"expected annual loss|financial exposure|how much risk|total risk|\beal\b", re.IGNORECASE),
        _handle_org_eal,
    ),
]


# Task 16 allow-list: every intent name Gemini is permitted to pick from,
# mapped to the exact same handler functions the rule-based router above
# uses. This is intentionally the ONLY way app/nlq/llm_router.py can reach
# code -- Gemini selects a name from this fixed dict, never a function, a
# DB query, or arbitrary code (build-spec.md risk R5).
ALLOWED_INTENTS: dict[str, callable] = {
    "org_eal": _handle_org_eal,
    "top_scenarios": _handle_top_scenarios,
    "highest_risk": _handle_highest_risk,
    "top_vulnerabilities": _handle_top_vulnerabilities,
    "eal_by_bu": _handle_eal_by_bu,
    "whatif_mfa": _handle_whatif_mfa,
    "delay_impact": _handle_delay_impact,
    "best_plan_for_budget": _handle_best_plan_for_budget,
    "compliance_gaps": _handle_compliance_gaps,
}


def _rule_based_answer(question: str) -> Answer:
    for pattern, handler in _INTENTS:
        if pattern.search(question):
            return handler(question)
    return Answer(
        text="I can't answer that yet. Try asking about highest risk, top vulnerabilities, "
        "EAL by business unit, a what-if on MFA, delay impact, the best plan for a budget, "
        "or compliance gaps.",
        intent=None,
    )


def answer(question: str) -> Answer:
    """L1 rule-based router by default; if GEMINI_API_KEY is set and valid,
    Task 16's allow-listed tool-calling layer (app/nlq/llm_router.py) is
    tried first for nicer phrasing. Gemini never computes or invents a
    number -- see llm_router.try_answer's docstring. Any failure there
    (missing/invalid key, network, rate limit) falls straight back to this
    same rule-based path, so the 9 existing intents are unaffected."""
    from app.nlq import llm_router

    llm_answer = llm_router.try_answer(question)
    if llm_answer is not None:
        return llm_answer
    return _rule_based_answer(question)
