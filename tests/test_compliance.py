"""PLAN.md Task 6 done-when test: fixing a finding flips its mapped
subcategory from gap to met. Also the R6 guardrail: no withdrawn CSF ID
ever appears.
"""

from __future__ import annotations

from app.compliance.csf_data import WITHDRAWN_CSF_1_1_IDS
from app.compliance.csf_import import import_csf
from app.compliance.status import compliance_status
from app.data import models as m


def test_import_csf_creates_functions_categories_and_starter_mapping(engine_db):
    session = engine_db()
    import_csf(session)
    session.commit()

    controls = session.query(m.FrameworkControl).all()
    control_ids = {c.control_id for c in controls}
    assert "PR.AA-03" in control_ids
    assert "PR.AA" in control_ids  # category-level row also present

    mappings = session.query(m.ControlMapping).all()
    assert 15 <= len(mappings) <= 20


def test_no_withdrawn_csf_id_ever_appears(engine_db):
    session = engine_db()
    import_csf(session)
    session.commit()

    control_ids = {c.control_id for c in session.query(m.FrameworkControl).all()}
    assert control_ids.isdisjoint(WITHDRAWN_CSF_1_1_IDS)


def test_fixing_a_finding_flips_gap_to_met(engine_db):
    session = engine_db()
    import_csf(session)

    asset = m.Asset(bu_id="bu-1", type="server", hostname="test-host", criticality=3.0)
    session.add(asset)
    session.flush()

    finding = m.Finding(asset_id=asset.id, finding_type="iam", rule_id="missing_mfa", status="open")
    session.add(finding)
    session.commit()
    session.close()

    rows_before = compliance_status(framework="NIST CSF", scope="org")
    status_before = next(r for r in rows_before if r["control_id"] == "PR.AA-03")
    assert status_before["status"] == "gap"

    session = engine_db()
    finding = session.query(m.Finding).filter_by(rule_id="missing_mfa").first()
    finding.status = "remediated"
    session.commit()
    session.close()

    rows_after = compliance_status(framework="NIST CSF", scope="org")
    status_after = next(r for r in rows_after if r["control_id"] == "PR.AA-03")
    assert status_after["status"] == "met"
