"""PLAN.md Task 10: top remediation actions ranked by a real risk score,
with KEV-listed CVEs weighted higher (build-spec.md section 3.3)."""

from __future__ import annotations

from app.data import models as m
from app.optimize.recommendations import top_finding_recommendations


def test_kev_listed_finding_ranks_above_equal_severity_non_kev(engine_db):
    session = engine_db()
    org = m.Organization(name="Test", sector="test", entity_type="test", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="BU")
    session.add(bu)
    session.flush()
    asset = m.Asset(bu_id=bu.id, type="server", hostname="host-1", criticality=3.0)
    session.add(asset)
    session.flush()

    session.add(m.Vulnerability(cve_id="CVE-2024-0001", in_kev=True))
    session.add(m.Vulnerability(cve_id="CVE-2024-0002", in_kev=False))
    session.add(
        m.Finding(asset_id=asset.id, finding_type="cve", cve_id="CVE-2024-0001", severity_weight=2.0, status="open")
    )
    session.add(
        m.Finding(asset_id=asset.id, finding_type="cve", cve_id="CVE-2024-0002", severity_weight=2.0, status="open")
    )
    session.commit()
    session.close()

    recs = top_finding_recommendations(limit=10)
    assert recs[0].rule_or_cve.startswith("CVE-2024-0001")
    assert recs[0].risk_score > recs[1].risk_score


def test_remediated_findings_are_excluded(engine_db):
    session = engine_db()
    org = m.Organization(name="Test", sector="test", entity_type="test", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="BU")
    session.add(bu)
    session.flush()
    asset = m.Asset(bu_id=bu.id, type="server", hostname="host-1", criticality=3.0)
    session.add(asset)
    session.add(m.FindingRule(rule_id="missing_mfa", title="MFA missing", category="iam", default_severity_weight=2.0))
    session.flush()
    session.add(m.Finding(asset_id=asset.id, finding_type="iam", rule_id="missing_mfa", status="remediated"))
    session.commit()
    session.close()

    recs = top_finding_recommendations(limit=10)
    assert recs == []
