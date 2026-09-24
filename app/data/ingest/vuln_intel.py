"""Real vulnerability intelligence: CISA KEV + FIRST EPSS (L1). Live, real
data attached to the synthetic software inventory, so KEV flags and EPSS
values are genuine (synthetic inputs, real mechanics, labeled which is
which).

Deliberately NOT called from `make seed` / app.data.seed.seed.seed():
that function's reproducibility guarantee ("same seed, same data") is
about the SYNTHETIC company, and a live feed changes daily by definition:
baking it into `seed()` would make `make seed` non-reproducible. Instead
this is its own step (`make fetch-vuln-intel`), logged as its own
INGEST_RUN with its own timestamp, exactly like the CSV importer
(provenance on every number: source, timestamp, run ID).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import requests

from app.config import settings
from app.data import models as m
from app.data.db import session_scope

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_URL = "https://api.first.org/data/v1/epss"

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
KEV_FIXTURE_PATH = FIXTURES_DIR / "kev_snapshot.json"
EPSS_FIXTURE_PATH = FIXTURES_DIR / "epss_snapshot.json"


def fetch_kev(timeout: float = 30.0) -> tuple[dict, str]:
    """Downloads the live CISA KEV catalog. Falls back to the frozen
    fixture (demo hardening: offline fallback if KEV/EPSS/Gemini
    unreachable) on any network failure so `docker compose up` reproduces
    the demo with no internet. Returns (catalog, source) where source is
    "live" or "offline_fixture"."""
    try:
        response = requests.get(KEV_URL, timeout=timeout)
        response.raise_for_status()
        return response.json(), "live"
    except requests.RequestException:
        return json.loads(KEV_FIXTURE_PATH.read_text()), "offline_fixture"


def fetch_epss(cve_ids: list[str], timeout: float = 20.0) -> tuple[dict[str, dict], str]:
    """Batched EPSS lookup (the API accepts a comma-separated CVE list, up to
    its own page limit). Returns ({cve_id: {"epss", "percentile", "date"}},
    source) where source is "live" or "offline_fixture"; missing CVEs (not
    yet scored, or absent from the frozen fixture) are simply absent."""
    if not cve_ids:
        return {}, "live"
    try:
        response = requests.get(EPSS_URL, params={"cve": ",".join(cve_ids)}, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        source = "live"
    except requests.RequestException:
        payload = json.loads(EPSS_FIXTURE_PATH.read_text())
        source = "offline_fixture"
    return {
        row["cve"]: {
            "epss": float(row["epss"]),
            "percentile": float(row["percentile"]),
            "date": row["date"],
        }
        for row in payload.get("data", [])
    }, source


def refresh_offline_fixture(n_cves: int = 15, seed: int | None = None) -> None:
    """Re-captures the frozen fixture from the live feeds, using the exact
    sample `import_vuln_intel` would draw for the given seed. Run this with
    internet access whenever the fixture should be refreshed; never called
    automatically (a frozen fixture that silently refreshes on whoever
    happens to have internet would defeat the point of freezing it)."""
    seed = seed if seed is not None else settings.default_seed
    rng = np.random.default_rng(seed)

    response = requests.get(KEV_URL, timeout=30.0)
    response.raise_for_status()
    catalog = response.json()
    all_vulns = catalog.get("vulnerabilities", [])
    sample_size = min(n_cves, len(all_vulns))
    sampled_indices = rng.choice(len(all_vulns), size=sample_size, replace=False)
    sampled = [all_vulns[i] for i in sampled_indices]

    KEV_FIXTURE_PATH.write_text(
        json.dumps(
            {"catalogVersion": catalog.get("catalogVersion"), "count": catalog.get("count"), "vulnerabilities": sampled},
            indent=2,
        )
    )

    cve_ids = [entry["cveID"] for entry in sampled]
    response = requests.get(EPSS_URL, params={"cve": ",".join(cve_ids)}, timeout=20.0)
    response.raise_for_status()
    EPSS_FIXTURE_PATH.write_text(json.dumps(response.json(), indent=2))


def import_vuln_intel(n_cves: int = 15, seed: int | None = None) -> dict:
    """Samples `n_cves` real KEV entries, fetches their EPSS scores, and
    attaches them to the synthetic inventory: a Software row per entry
    (real vendor/product names from KEV), linked via AssetSoftware to a few
    existing assets, plus a Finding per link. Requires the synthetic company
    to already be seeded (assets must exist to attach software to).
    """
    seed = seed if seed is not None else settings.default_seed
    rng = np.random.default_rng(seed)

    kev_catalog, kev_source = fetch_kev()
    all_vulns = kev_catalog.get("vulnerabilities", [])
    if not all_vulns:
        raise ValueError("CISA KEV feed and offline fixture both returned no vulnerabilities")

    sample_size = min(n_cves, len(all_vulns))
    sampled_indices = rng.choice(len(all_vulns), size=sample_size, replace=False)
    sampled = [all_vulns[i] for i in sampled_indices]

    cve_ids = [entry["cveID"] for entry in sampled]
    epss_scores, epss_source = fetch_epss(cve_ids)

    with session_scope() as session:
        source = m.DataSource(
            name="CISA KEV + FIRST EPSS",
            kind="api",
            licence_note=(
                "CISA KEV: public domain / CC0. FIRST EPSS: public, no auth. "
                f"kev_source={kev_source}, epss_source={epss_source} "
                "(offline_fixture = frozen snapshot used because the live feed "
                "was unreachable; see app/data/fixtures/README.md)."
            ),
        )
        session.add(source)
        session.flush()

        run = m.IngestRun(
            source_id=source.id,
            started_at=dt.datetime.now(dt.UTC),
            status="running",
            rows_in=len(sampled),
        )
        session.add(run)
        session.flush()

        assets = session.query(m.Asset).all()
        if not assets:
            raise ValueError("No assets found -- run `make seed` before `make fetch-vuln-intel`")

        n_created_vulns = 0
        n_created_findings = 0
        rejections: list[dict] = []

        for entry in sampled:
            cve_id = entry["cveID"]
            if session.get(m.Vulnerability, cve_id) is not None:
                rejections.append({"cve_id": cve_id, "reason": "already in catalogue"})
                continue

            epss = epss_scores.get(cve_id)
            date_added = (
                dt.datetime.strptime(entry["dateAdded"], "%Y-%m-%d").replace(tzinfo=dt.UTC).date()
                if entry.get("dateAdded")
                else None
            )

            session.add(
                m.Vulnerability(
                    cve_id=cve_id,
                    cvss_score=None,  # not provided by KEV/EPSS; CVE List V5/NVD enrichment is Task 14 (L2)
                    score_source="default",
                    cwe=(entry.get("cwes") or [None])[0],
                    epss=epss["epss"] if epss else None,
                    epss_percentile=epss["percentile"] if epss else None,
                    epss_date=(
                        dt.datetime.strptime(epss["date"], "%Y-%m-%d").replace(tzinfo=dt.UTC)
                        if epss
                        else None
                    ),
                    in_kev=True,
                    kev_date_added=date_added,
                    kev_ransomware_use=entry.get("knownRansomwareCampaignUse"),
                    nvd_status=None,
                )
            )
            n_created_vulns += 1

            software = m.Software(
                vendor=entry.get("vendorProject", "unknown"),
                product=entry.get("product", "unknown"),
                version="unknown",
            )
            session.add(software)
            session.flush()

            n_links = int(rng.integers(1, 3))
            linked_assets = rng.choice(assets, size=min(n_links, len(assets)), replace=False)
            for asset in linked_assets:
                # The synthetic assets carry no real software inventory, so
                # there is nothing to match this real KEV vendor/product
                # against -- the asset is an arbitrary sampled placement, not
                # a verified match. Recorded honestly rather than implying
                # precision the data doesn't have (see AssetSoftware docstring).
                session.add(
                    m.AssetSoftware(
                        asset_id=asset.id,
                        software_id=software.id,
                        match_basis="synthetic_no_inventory",
                        match_confidence=0.0,
                    )
                )
                status = "remediated" if rng.random() < 0.3 else "open"
                session.add(
                    m.Finding(
                        asset_id=asset.id,
                        finding_type="cve",
                        cve_id=cve_id,
                        severity_weight=2.0,
                        status=status,
                        source_id=source.id,
                    )
                )
                n_created_findings += 1

        run.finished_at = dt.datetime.now(dt.UTC)
        run.status = "completed"
        run.rows_rejected = len(rejections)
        run.rejection_log = {"rejections": rejections}

        return {
            "ingest_run_id": run.id,
            "catalog_version": kev_catalog.get("catalogVersion"),
            "kev_total_count": kev_catalog.get("count"),
            "kev_source": kev_source,
            "epss_source": epss_source,
            "n_sampled": len(sampled),
            "n_created_vulns": n_created_vulns,
            "n_created_findings": n_created_findings,
            "n_rejected": len(rejections),
        }
