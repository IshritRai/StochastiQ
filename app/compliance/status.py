"""compliance_status(framework, scope) -> DataFrame, per build-spec.md section 2.2.

Status is computed, never typed in (build-spec.md section 3.6's done-when
test: "fixing a finding turns its mapped subcategory from gap to met").
"""

from __future__ import annotations

import datetime as dt

from app.data import models as m
from app.data.db import session_scope

# Coverage thresholds for control-type-backed mappings (e.g. patch management
# coverage -> ID.RA-01). ASSUMPTION: no verified public threshold exists for
# "how much control coverage counts as compliant" (same gap PLAN.md section 7
# documents for control efficacy); revisit once real assessment criteria exist.
_COVERAGE_MET_THRESHOLD = 0.80
_COVERAGE_PARTIAL_THRESHOLD = 0.40

_STATUS_RANK = {"met": 0, "partial": 1, "gap": 2, "unknown": -1}


def _worst_status(statuses: list[str]) -> str:
    non_unknown = [s for s in statuses if s != "unknown"]
    if not non_unknown:
        return "unknown"
    return max(non_unknown, key=lambda s: _STATUS_RANK[s])


def _finding_rule_status(session, rule_id: str) -> str:
    findings = session.query(m.Finding).filter_by(rule_id=rule_id).all()
    if not findings:
        return "unknown"
    if any(f.status == "open" for f in findings):
        return "gap"
    return "met"


def _control_type_status(session, control_type_id: str) -> str:
    states = session.query(m.ControlState).filter_by(control_type_id=control_type_id).all()
    if not states:
        return "unknown"
    avg_coverage = sum(s.coverage_pct for s in states) / len(states)
    if avg_coverage >= _COVERAGE_MET_THRESHOLD:
        return "met"
    if avg_coverage >= _COVERAGE_PARTIAL_THRESHOLD:
        return "partial"
    return "gap"


def compliance_status(framework: str = "NIST CSF", scope: str = "org") -> list[dict]:
    """Computes and persists ComplianceStatus rows for every active,
    subcategory-level FrameworkControl in `framework`. Returns the rows as
    plain dicts (a DataFrame-shaped list, per the build-spec.md contract)."""
    with session_scope() as session:
        fw = session.query(m.Framework).filter_by(name=framework, retired=False).first()
        if fw is None:
            raise ValueError(f"Unknown or retired framework: {framework!r}")

        controls = (
            session.query(m.FrameworkControl)
            .filter_by(framework_id=fw.id, status="active")
            .filter(m.FrameworkControl.parent_id.isnot(None))  # subcategory-level only
            .all()
        )

        rows = []
        for control in controls:
            mappings = (
                session.query(m.ControlMapping)
                .filter_by(framework_control_id=control.id)
                .all()
            )
            statuses = []
            basis_mappings = []
            for mapping in mappings:
                if mapping.from_kind == "finding_rule":
                    status = _finding_rule_status(session, mapping.from_id)
                else:
                    status = _control_type_status(session, mapping.from_id)
                statuses.append(status)
                basis_mappings.append(
                    {"from_kind": mapping.from_kind, "from_id": mapping.from_id, "status": status}
                )

            overall = _worst_status(statuses)
            row = {
                "framework_control_id": control.id,
                "control_id": control.control_id,
                "short_title": control.short_title,
                "scope": scope,
                "status": overall,
                "basis": {"mappings": basis_mappings},
            }
            rows.append(row)

            session.add(
                m.ComplianceStatus(
                    framework_control_id=control.id,
                    scope=scope,
                    computed_at=dt.datetime.now(dt.UTC),
                    status=overall,
                    basis=row["basis"],
                )
            )

        return rows
