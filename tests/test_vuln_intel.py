"""PLAN.md Task 8: real KEV/EPSS data attached to the synthetic inventory.

HTTP calls are mocked (fetch_kev/fetch_epss monkeypatched) so this test
suite stays offline and deterministic -- the live network path is exercised
manually via `make fetch-vuln-intel`, not in CI, matching build-spec.md's
"offline fallback" requirement (a test suite that depends on a live feed
being up is itself a flakiness risk).
"""

from __future__ import annotations

import requests

from app.data import models as m
from app.data.ingest import vuln_intel
from app.optimize.recommendations import top_finding_recommendations

_FAKE_KEV_CATALOG = {
    "catalogVersion": "2026.01.01",
    "count": 2,
    "vulnerabilities": [
        {
            "cveID": "CVE-2021-44228",
            "vendorProject": "Apache",
            "product": "Log4j2",
            "vulnerabilityName": "Apache Log4j2 RCE",
            "dateAdded": "2021-12-10",
            "knownRansomwareCampaignUse": "Known",
            "cwes": ["CWE-502"],
        },
        {
            "cveID": "CVE-2017-0144",
            "vendorProject": "Microsoft",
            "product": "Windows SMB",
            "vulnerabilityName": "EternalBlue",
            "dateAdded": "2017-05-12",
            "knownRansomwareCampaignUse": "Known",
            "cwes": ["CWE-20"],
        },
    ],
}

_FAKE_EPSS_SCORES = {
    "CVE-2021-44228": {"epss": 0.9999, "percentile": 1.0, "date": "2026-01-01"},
    "CVE-2017-0144": {"epss": 0.9923, "percentile": 0.9993, "date": "2026-01-01"},
}


def _seed_minimal_org(session, n_assets=5):
    org = m.Organization(name="Test", sector="test", entity_type="test", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="BU")
    session.add(bu)
    session.flush()
    assets = []
    for i in range(n_assets):
        asset = m.Asset(bu_id=bu.id, type="server", hostname=f"host-{i}", criticality=3.0)
        session.add(asset)
        assets.append(asset)
    session.commit()


def test_import_vuln_intel_creates_real_kev_backed_rows(engine_db, monkeypatch):
    session = engine_db()
    _seed_minimal_org(session)
    session.close()

    monkeypatch.setattr(vuln_intel, "fetch_kev", lambda timeout=30.0: (_FAKE_KEV_CATALOG, "live"))
    monkeypatch.setattr(vuln_intel, "fetch_epss", lambda cve_ids, timeout=20.0: (_FAKE_EPSS_SCORES, "live"))

    result = vuln_intel.import_vuln_intel(n_cves=2, seed=42)

    assert result["n_created_vulns"] == 2
    assert result["catalog_version"] == "2026.01.01"

    session = engine_db()
    vulns = {v.cve_id: v for v in session.query(m.Vulnerability).all()}
    assert vulns["CVE-2021-44228"].in_kev is True
    assert vulns["CVE-2021-44228"].epss == 0.9999
    assert vulns["CVE-2021-44228"].kev_ransomware_use == "Known"

    findings = session.query(m.Finding).filter(m.Finding.cve_id.isnot(None)).all()
    assert len(findings) >= 2


def test_removing_kev_flag_changes_finding_ranking(engine_db, monkeypatch):
    """build-spec.md section 3.1 done-when: 'removing a CVE's KEV flag
    changes its finding weight.'"""
    session = engine_db()
    _seed_minimal_org(session)
    session.close()

    monkeypatch.setattr(vuln_intel, "fetch_kev", lambda timeout=30.0: (_FAKE_KEV_CATALOG, "live"))
    monkeypatch.setattr(vuln_intel, "fetch_epss", lambda cve_ids, timeout=20.0: (_FAKE_EPSS_SCORES, "live"))
    vuln_intel.import_vuln_intel(n_cves=2, seed=42)

    recs_before = top_finding_recommendations(limit=10)
    log4j_before = next(r for r in recs_before if r.rule_or_cve.startswith("CVE-2021-44228"))
    assert "KEV" in log4j_before.rule_or_cve

    session = engine_db()
    vuln = session.get(m.Vulnerability, "CVE-2021-44228")
    vuln.in_kev = False
    session.commit()
    session.close()

    recs_after = top_finding_recommendations(limit=10)
    log4j_after = next(r for r in recs_after if r.rule_or_cve.startswith("CVE-2021-44228"))
    assert "KEV" not in log4j_after.rule_or_cve
    assert log4j_after.risk_score < log4j_before.risk_score


def test_fetch_kev_falls_back_to_offline_fixture_when_live_feed_unreachable(monkeypatch):
    """PLAN.md Task 21 done-when: `docker compose up` reproduces the exact
    demo state with no internet -- the live CISA KEV call must degrade to
    the frozen fixture rather than raise."""

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("simulated: no internet")

    monkeypatch.setattr(requests, "get", _raise)

    catalog, source = vuln_intel.fetch_kev()
    assert source == "offline_fixture"
    assert catalog["vulnerabilities"]

    scores, epss_source = vuln_intel.fetch_epss([catalog["vulnerabilities"][0]["cveID"]])
    assert epss_source == "offline_fixture"
    assert isinstance(scores, dict)


def test_import_vuln_intel_succeeds_with_no_network(engine_db, monkeypatch):
    """End-to-end: the whole import (not just the fetch helpers) must
    complete offline, since this is what `docker compose up` with no
    internet actually calls."""
    session = engine_db()
    _seed_minimal_org(session)
    session.close()

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("simulated: no internet")

    monkeypatch.setattr(requests, "get", _raise)

    result = vuln_intel.import_vuln_intel(n_cves=5, seed=42)
    assert result["kev_source"] == "offline_fixture"
    assert result["epss_source"] == "offline_fixture"
    assert result["n_created_vulns"] > 0
