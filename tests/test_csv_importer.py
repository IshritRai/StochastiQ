"""PLAN.md Task 9 done-when test: importing an edited CSV changes downstream
figures; a malformed row is rejected and logged, not silently dropped."""

from __future__ import annotations

from app.data import models as m
from app.data.ingest.csv_importer import import_assets_csv, import_findings_csv


def test_import_assets_csv_creates_valid_rows_and_rejects_invalid_ones(engine_db, tmp_path):
    session = engine_db()
    org = m.Organization(name="Test Org", sector="test", entity_type="test", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="Test BU")
    session.add(bu)
    session.commit()
    bu_id = bu.id
    session.close()

    csv_path = tmp_path / "assets.csv"
    csv_path.write_text(
        "bu_id,type,hostname,environment,data_sensitivity\n"
        f"{bu_id},server,good-host-1,prod,3\n"
        "not-a-real-bu,server,bad-bu-host,prod,3\n"
        f"{bu_id},server,,prod,3\n"  # missing hostname
        f"{bu_id},server,bad-sensitivity-host,prod,9\n"  # out of range
    )

    result = import_assets_csv(str(csv_path))

    assert result["rows_in"] == 4
    assert result["rows_created"] == 1
    assert result["rows_rejected"] == 3

    session = engine_db()
    ingest_run = session.get(m.IngestRun, result["ingest_run_id"])
    assert ingest_run.rows_rejected == 3
    assert len(ingest_run.rejection_log["rejections"]) == 3
    assets = session.query(m.Asset).all()
    assert len(assets) == 1
    assert assets[0].hostname == "good-host-1"


def test_import_findings_csv_rejects_unknown_references(engine_db, tmp_path):
    session = engine_db()
    org = m.Organization(name="Test Org", sector="test", entity_type="test", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="Test BU")
    session.add(bu)
    session.flush()
    asset = m.Asset(bu_id=bu.id, type="server", hostname="host-1")
    session.add(asset)
    session.add(m.FindingRule(rule_id="missing_mfa", title="MFA missing", category="iam", default_severity_weight=2.0))
    session.commit()
    asset_id = asset.id
    session.close()

    csv_path = tmp_path / "findings.csv"
    csv_path.write_text(
        "asset_id,finding_type,rule_id,status\n"
        f"{asset_id},iam,missing_mfa,open\n"
        "unknown-asset,iam,missing_mfa,open\n"
        f"{asset_id},iam,unknown_rule,open\n"
    )

    result = import_findings_csv(str(csv_path))

    assert result["rows_in"] == 3
    assert result["rows_created"] == 1
    assert result["rows_rejected"] == 2

    session = engine_db()
    findings = session.query(m.Finding).all()
    assert len(findings) == 1
    assert findings[0].rule_id == "missing_mfa"
