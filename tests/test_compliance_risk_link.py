"""PLAN.md Task 18: risk-to-compliance rupee link and EAL trend."""

from __future__ import annotations

import datetime as dt

from app.compliance.risk_link import compliance_risk_eal
from app.data import models as m
from app.engine.trend import org_eal_trend


def _seed_framework_with_gap(session, run_eal=100_000.0):
    fw = m.Framework(name="NIST CSF", version="2.0", licence_tier="public", retired=False)
    session.add(fw)
    session.flush()

    control_a = m.FrameworkControl(
        framework_id=fw.id, control_id="ID.AM-01", short_title="Hardware inventory", status="active"
    )
    control_b = m.FrameworkControl(
        framework_id=fw.id, control_id="PR.AA-03", short_title="MFA", status="active"
    )
    session.add_all([control_a, control_b])
    session.flush()

    org = m.Organization(name="T", sector="t", entity_type="t", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="BU")
    session.add(bu)
    session.flush()
    asset = m.Asset(bu_id=bu.id, type="server", hostname="h1", criticality=3.0)
    session.add(asset)
    session.flush()

    session.add(m.FindingRule(rule_id="no_asset_inventory", title="x", category="coverage_gap"))
    session.add(m.FindingRule(rule_id="missing_mfa", title="y", category="iam"))
    session.flush()

    session.add(m.Finding(asset_id=asset.id, finding_type="coverage_gap", rule_id="no_asset_inventory", severity_weight=3.0, status="open"))
    session.add(m.Finding(asset_id=asset.id, finding_type="iam", rule_id="missing_mfa", severity_weight=1.0, status="open"))
    session.flush()

    session.add(m.ControlMapping(from_kind="finding_rule", from_id="no_asset_inventory", framework_control_id=control_a.id, source="starter"))
    session.add(m.ControlMapping(from_kind="finding_rule", from_id="missing_mfa", framework_control_id=control_b.id, source="starter"))
    session.flush()

    session.add(m.ComplianceStatus(framework_control_id=control_a.id, scope="org", status="gap", basis={}))
    session.add(m.ComplianceStatus(framework_control_id=control_b.id, scope="org", status="gap", basis={}))
    session.flush()

    run = m.SimulationRun(
        scenario_id=None,
        seed=42,
        n_iter=100,
        inputs_hash="h",
        engine_version="0.1.0",
        eal=run_eal,
        var95=0.0,
        var99=0.0,
        eal_std_err=0.0,
    )
    session.add(run)
    session.commit()
    return run.id


def test_compliance_risk_eal_sums_to_run_eal_across_gap_controls(engine_db):
    session = engine_db()
    run_id = _seed_framework_with_gap(session, run_eal=100_000.0)
    session.close()

    rows = compliance_risk_eal(run_id)
    assert len(rows) == 2
    total = sum(r["eal_at_risk_inr"] for r in rows)
    assert total == 100_000.0

    # gap weight 3.0 vs 1.0 -> 75%/25% split
    by_control = {r["control_id"]: r for r in rows}
    assert by_control["ID.AM-01"]["eal_at_risk_inr"] == 75_000.0
    assert by_control["PR.AA-03"]["eal_at_risk_inr"] == 25_000.0


def test_compliance_risk_eal_empty_when_no_gap_weight(engine_db):
    session = engine_db()
    fw = m.Framework(name="NIST CSF", version="2.0", retired=False)
    session.add(fw)
    session.flush()
    run = m.SimulationRun(
        scenario_id=None, seed=1, n_iter=10, inputs_hash="h", engine_version="0.1.0",
        eal=1.0, var95=0.0, var99=0.0, eal_std_err=0.0,
    )
    session.add(run)
    session.commit()
    run_id = run.id
    session.close()

    assert compliance_risk_eal(run_id) == []


def test_org_eal_trend_only_includes_matching_seed_org_level_runs(engine_db):
    session = engine_db()
    base = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    session.add(m.SimulationRun(
        scenario_id=None, seed=42, n_iter=100, inputs_hash="a", engine_version="v",
        eal=10.0, var95=0.0, var99=0.0, eal_std_err=0.0, snapshot_at=base,
    ))
    session.add(m.SimulationRun(
        scenario_id=None, seed=42, n_iter=100, inputs_hash="b", engine_version="v",
        eal=20.0, var95=0.0, var99=0.0, eal_std_err=0.0, snapshot_at=base + dt.timedelta(days=1),
    ))
    # different seed -- must be excluded
    session.add(m.SimulationRun(
        scenario_id=None, seed=99, n_iter=100, inputs_hash="c", engine_version="v",
        eal=999.0, var95=0.0, var99=0.0, eal_std_err=0.0, snapshot_at=base,
    ))
    # scenario-level run -- must be excluded
    session.add(m.SimulationRun(
        scenario_id="scenario-1", seed=42, n_iter=100, inputs_hash="d", engine_version="v",
        eal=999.0, var95=0.0, var99=0.0, eal_std_err=0.0, snapshot_at=base,
    ))
    session.commit()
    session.close()

    trend = org_eal_trend(seed=42)
    assert [row["eal"] for row in trend] == [10.0, 20.0]
