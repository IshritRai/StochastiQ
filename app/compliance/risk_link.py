"""Risk-to-compliance rupee link (PLAN.md Task 18): how much of the org's
EAL is attributable to each unmet (gap/partial) framework control.

Method (documented L2 simplification, `is_assumption=true` in spirit):
for every non-met control, its "gap weight" is the sum of severity_weight
across its mapped finding_rule's OPEN findings, plus (1 - coverage_pct) for
every mapped control_type (an uncovered control contributes weight
proportional to how uncovered it is). A control's EAL share is then
run.eal * (its gap weight / total gap weight across all non-met, mapped
controls) -- the SAME allocation-by-weight approach `attribute_impl`
already uses for assets (build-spec.md section 3.2), just reused here for
framework controls instead of assets. This is a real, run-traceable number
(CLAUDE.md rule 1/2): it always sums to exactly the run's EAL across the
controls it covers, and every row is stamped with `run_id`.
"""

from __future__ import annotations

from app.data import models as m
from app.data.db import session_scope


def _finding_rule_gap_weight(session, rule_id: str) -> float:
    findings = session.query(m.Finding).filter_by(rule_id=rule_id, status="open").all()
    return sum(f.severity_weight for f in findings)


def _control_type_gap_weight(session, control_type_id: str) -> float:
    states = session.query(m.ControlState).filter_by(control_type_id=control_type_id).all()
    if not states:
        return 0.0
    avg_coverage = sum(s.coverage_pct for s in states) / len(states)
    return max(0.0, 1.0 - avg_coverage)


def compliance_risk_eal(run_id: str, framework: str = "NIST CSF") -> list[dict]:
    """Returns, for every non-met (gap/partial) FrameworkControl in
    `framework` that has at least one mapping and nonzero gap weight, the
    EAL (INR) of `run_id` attributable to it. Rows sum to exactly
    run.eal * (covered gap weight / total gap weight) <= run.eal."""
    with session_scope() as session:
        run = session.get(m.SimulationRun, run_id)
        if run is None:
            raise ValueError(f"Unknown run_id: {run_id!r}")

        fw = session.query(m.Framework).filter_by(name=framework, retired=False).first()
        if fw is None:
            raise ValueError(f"Unknown or retired framework: {framework!r}")

        latest_status: dict[str, m.ComplianceStatus] = {}
        statuses = (
            session.query(m.ComplianceStatus)
            .join(m.FrameworkControl, m.ComplianceStatus.framework_control_id == m.FrameworkControl.id)
            .filter(m.FrameworkControl.framework_id == fw.id)
            .order_by(m.ComplianceStatus.computed_at)
            .all()
        )
        for status in statuses:
            latest_status[status.framework_control_id] = status  # last write wins: most recent

        controls = {
            c.id: c
            for c in session.query(m.FrameworkControl)
            .filter_by(framework_id=fw.id, status="active")
            .all()
        }

        gap_weights: dict[str, float] = {}
        for control_id, status in latest_status.items():
            if status.status not in ("gap", "partial") or control_id not in controls:
                continue
            mappings = session.query(m.ControlMapping).filter_by(framework_control_id=control_id).all()
            weight = 0.0
            for mp in mappings:
                if mp.from_kind == "finding_rule":
                    weight += _finding_rule_gap_weight(session, mp.from_id)
                else:
                    weight += _control_type_gap_weight(session, mp.from_id)
            if weight > 0:
                gap_weights[control_id] = weight

        total_weight = sum(gap_weights.values())
        if total_weight == 0:
            return []

        rows = []
        for control_id, weight in gap_weights.items():
            control = controls[control_id]
            status = latest_status[control_id]
            rows.append(
                {
                    "run_id": run_id,
                    "control_id": control.control_id,
                    "short_title": control.short_title,
                    "status": status.status,
                    "gap_weight": weight,
                    "eal_at_risk_inr": run.eal * (weight / total_weight),
                }
            )
        rows.sort(key=lambda r: r["eal_at_risk_inr"], reverse=True)
        return rows
