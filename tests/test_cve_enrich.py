"""PLAN.md Task 14: CVE List V5 + Vulnrichment (CISA-ADP) precedence rule,
and OSV package matching. HTTP calls are mocked, matching test_vuln_intel.py's
offline-deterministic pattern; the live path is exercised via
`make enrich-vuln-intel`.
"""

from __future__ import annotations

from app.data import models as m
from app.data.ingest import cve_enrich

_CNA_RECORD = {
    "containers": {
        "cna": {
            "metrics": [{"cvssV3_1": {"baseScore": 9.8, "vectorString": "CVSS:3.1/AV:N"}}]
        },
        "adp": [],
    }
}

_ADP_ONLY_RECORD = {
    "containers": {
        "cna": {"metrics": []},
        "adp": [
            {"title": "CVE Program Container", "references": []},
            {"metrics": [{"cvssV3_1": {"baseScore": 7.5, "vectorString": "CVSS:3.1/AV:N"}}]},
        ],
    }
}

_EMPTY_RECORD = {"containers": {"cna": {"metrics": []}, "adp": []}}


def _seed_vulns(session, rows):
    for cve_id in rows:
        session.add(m.Vulnerability(cve_id=cve_id, score_source="default"))
    session.commit()


def test_precedence_prefers_cna_over_adp_and_nvd(engine_db, monkeypatch):
    session = engine_db()
    _seed_vulns(session, ["CVE-2023-0001"])
    session.close()

    monkeypatch.setattr(cve_enrich, "fetch_cvelist_record", lambda cve_id: _CNA_RECORD)
    monkeypatch.setattr(
        cve_enrich, "fetch_nvd_cvss", lambda cve_id: (1.0, "should-not-be-used")
    )

    result = cve_enrich.enrich_cvss_scores(["CVE-2023-0001"])
    assert result["by_source"]["cna"] == 1

    session = engine_db()
    vuln = session.get(m.Vulnerability, "CVE-2023-0001")
    assert vuln.score_source == "cna"
    assert vuln.cvss_score == 9.8


def test_precedence_falls_back_to_adp_when_cna_has_no_metrics(engine_db, monkeypatch):
    session = engine_db()
    _seed_vulns(session, ["CVE-2023-0002"])
    session.close()

    monkeypatch.setattr(cve_enrich, "fetch_cvelist_record", lambda cve_id: _ADP_ONLY_RECORD)
    monkeypatch.setattr(cve_enrich, "fetch_nvd_cvss", lambda cve_id: (1.0, "should-not-be-used"))

    cve_enrich.enrich_cvss_scores(["CVE-2023-0002"])

    session = engine_db()
    vuln = session.get(m.Vulnerability, "CVE-2023-0002")
    assert vuln.score_source == "adp"
    assert vuln.cvss_score == 7.5


def test_precedence_falls_back_to_nvd_when_cvelist_has_nothing(engine_db, monkeypatch):
    session = engine_db()
    _seed_vulns(session, ["CVE-2023-0003"])
    session.close()

    monkeypatch.setattr(cve_enrich, "fetch_cvelist_record", lambda cve_id: _EMPTY_RECORD)
    monkeypatch.setattr(cve_enrich, "fetch_nvd_cvss", lambda cve_id: (5.5, "CVSS:3.1/AV:L"))

    cve_enrich.enrich_cvss_scores(["CVE-2023-0003"])

    session = engine_db()
    vuln = session.get(m.Vulnerability, "CVE-2023-0003")
    assert vuln.score_source == "nvd"
    assert vuln.cvss_score == 5.5


def test_precedence_falls_back_to_default_when_nothing_found(engine_db, monkeypatch):
    session = engine_db()
    _seed_vulns(session, ["CVE-2023-0004"])
    session.close()

    monkeypatch.setattr(cve_enrich, "fetch_cvelist_record", lambda cve_id: None)
    monkeypatch.setattr(cve_enrich, "fetch_nvd_cvss", lambda cve_id: None)

    cve_enrich.enrich_cvss_scores(["CVE-2023-0004"])

    session = engine_db()
    vuln = session.get(m.Vulnerability, "CVE-2023-0004")
    assert vuln.score_source == "default"
    assert vuln.cvss_score is None


def test_enrich_is_idempotent_and_does_not_downgrade_precedence(engine_db, monkeypatch):
    """Once a row is resolved at the cna tier, a re-run must not silently
    fall back to a lower-precedence source even if the mock changes."""
    session = engine_db()
    _seed_vulns(session, ["CVE-2023-0005"])
    session.close()

    monkeypatch.setattr(cve_enrich, "fetch_cvelist_record", lambda cve_id: _CNA_RECORD)
    monkeypatch.setattr(cve_enrich, "fetch_nvd_cvss", lambda cve_id: None)
    cve_enrich.enrich_cvss_scores(["CVE-2023-0005"])

    # Simulate the CNA record disappearing on a later run.
    monkeypatch.setattr(cve_enrich, "fetch_cvelist_record", lambda cve_id: None)
    result = cve_enrich.enrich_cvss_scores(["CVE-2023-0005"])
    assert result["n_updated"] == 0

    session = engine_db()
    vuln = session.get(m.Vulnerability, "CVE-2023-0005")
    assert vuln.score_source == "cna"
    assert vuln.cvss_score == 9.8


def test_osv_package_match_confidence_levels(engine_db, monkeypatch):
    session = engine_db()
    org = m.Organization(name="T", sector="t", entity_type="t", revenue_inr=1.0, size_band="small")
    session.add(org)
    session.flush()
    bu = m.BusinessUnit(org_id=org.id, name="BU")
    session.add(bu)
    session.flush()
    asset = m.Asset(bu_id=bu.id, type="server", hostname="h1", criticality=3.0)
    session.add(asset)
    session.flush()

    sw_exact = m.Software(vendor="Apache", product="Log4j2", version="2.14.1")
    sw_partial = m.Software(vendor="Microsoft", product="Windows", version="unknown")
    sw_none = m.Software(vendor="Acme", product="Widget", version="1.0")
    session.add_all([sw_exact, sw_partial, sw_none])
    session.flush()

    links = [
        m.AssetSoftware(asset_id=asset.id, software_id=sw_exact.id, match_basis="synthetic_no_inventory", match_confidence=0.0),
        m.AssetSoftware(asset_id=asset.id, software_id=sw_partial.id, match_basis="synthetic_no_inventory", match_confidence=0.0),
        m.AssetSoftware(asset_id=asset.id, software_id=sw_none.id, match_basis="synthetic_no_inventory", match_confidence=0.0),
    ]
    session.add_all(links)
    session.commit()
    link_ids = [link.id for link in links]
    session.close()

    def fake_osv_query(vendor, product, version, timeout=15.0):
        if product == "Log4j2":
            return [{"id": "GHSA-xxxx"}]
        if product == "Windows":
            return [{"id": "GHSA-yyyy"}]
        return []

    monkeypatch.setattr(cve_enrich, "_osv_query_package", fake_osv_query)

    result = cve_enrich.enrich_package_matches()
    assert result["n_exact"] == 1
    assert result["n_partial"] == 1
    assert result["n_none"] == 1

    session = engine_db()
    by_id = {row.id: row for row in session.query(m.AssetSoftware).filter(m.AssetSoftware.id.in_(link_ids))}
    assert by_id[link_ids[0]].match_confidence == 1.0
    assert by_id[link_ids[1]].match_confidence == 0.5
    assert by_id[link_ids[2]].match_confidence == 0.0
