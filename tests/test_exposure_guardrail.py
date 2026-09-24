"""PLAN.md Task 15 guardrail test, written FIRST per CLAUDE.md ("tests
before dependents build on a function") and build-spec.md risk R1: an
extreme finding population must never move EAL beyond the configured
ExposureMult bound (settings.exposure_mult_hi / exposure_mult_lo).

This test is written and run to FAIL against the pre-Task-15 engine (no
telemetry-driven exposure module exists yet, and run_scenario_impl always
passes exposure_mult=1.0 unless a caller supplies an override) before
app/engine/exposure.py is implemented.
"""

from __future__ import annotations

from app.config import settings
from app.data import models as m
from app.engine.contracts import run_scenario
from tests.conftest import make_scenario


def _seed_org_with_findings(session, n_assets, severity_weight, in_kev, epss):
    org = m.Organization(name="T", sector="t", entity_type="t", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="BU")
    session.add(bu)
    session.flush()

    vuln = m.Vulnerability(cve_id="CVE-9999-0001", in_kev=in_kev, epss=epss, score_source="default")
    session.add(vuln)

    for i in range(n_assets):
        asset = m.Asset(bu_id=bu.id, type="server", hostname=f"h{i}", criticality=3.0)
        session.add(asset)
        session.flush()
        session.add(
            m.Finding(
                asset_id=asset.id,
                finding_type="cve",
                cve_id="CVE-9999-0001",
                severity_weight=severity_weight,
                status="open",
            )
        )
    session.commit()


def test_extreme_open_findings_cannot_push_eal_past_the_exposure_mult_bound(engine_db):
    """Feeding a scenario an absurdly extreme open-finding population (huge
    severity_weight, in_kev=True, epss=1.0) must give EXACTLY the same EAL
    as directly overriding exposure_mult=settings.exposure_mult_hi -- i.e.
    the telemetry-derived multiplier must be clipped to the configured
    bound, not allowed to blow past it linearly with finding severity."""
    session = engine_db()
    make_scenario(session, "scenario-1", tef=(0.5, 1.0, 2.0), vuln=(0.2, 0.4, 0.6))
    _seed_org_with_findings(session, n_assets=20, severity_weight=1_000.0, in_kev=True, epss=1.0)
    session.close()

    seed = 42
    # Telemetry-driven: no explicit exposure_mult override, computed from
    # the (extreme) open findings in the DB by app.engine.exposure.
    extreme_result = run_scenario("scenario-1", overrides={}, seed=seed)

    # Directly override to the hard bound for comparison.
    bounded_result = run_scenario(
        "scenario-1", overrides={"exposure_mult": settings.exposure_mult_hi}, seed=seed
    )

    assert extreme_result.summary.eal == bounded_result.summary.eal


def test_no_open_findings_gives_neutral_exposure_mult(engine_db):
    """With no open findings at all, the telemetry-driven exposure_mult must
    be the identity 1.0 -- no findings, no exposure adjustment."""
    session = engine_db()
    make_scenario(session, "scenario-1", tef=(0.5, 1.0, 2.0), vuln=(0.2, 0.4, 0.6))
    session.commit()
    session.close()

    seed = 42
    result = run_scenario("scenario-1", overrides={}, seed=seed)
    identity_result = run_scenario("scenario-1", overrides={"exposure_mult": 1.0}, seed=seed)
    assert result.summary.eal == identity_result.summary.eal
