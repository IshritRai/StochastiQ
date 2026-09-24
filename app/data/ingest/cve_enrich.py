"""L2 vulnerability enrichment (PLAN.md Task 14).

Two independent enrichments, both logged as their own INGEST_RUN with
source/timestamp/run ID (CLAUDE.md rule 2):

1. CVSS score precedence: CNA -> CISA-ADP (Vulnrichment) -> NVD -> default
   prior. Pulled from the CVE List V5 GitHub mirror (CNA + ADP containers
   live in the same JSON record) and the NVD REST API (fallback only, since
   NVD's own analysis is explicitly last in the precedence order per the
   task). `Vulnerability.score_source` records which tier won.
2. OSV / GitHub Advisories package-version matching: for each Software row
   attached via AssetSoftware, query OSV.dev for advisories affecting that
   vendor/product/version and record a `match_confidence` on AssetSoftware
   (exact version match = 1.0, package-name-only match = 0.5, no match
   unchanged from the L1 placeholder of 0.0).

Both are read-only enrichments over rows created by `make seed` and
`make fetch-vuln-intel` -- neither one fabricates a CVE or a package; every
enriched value traces back to what CVE List V5 / NVD / OSV actually returned
for that exact ID (CLAUDE.md rule 1).
"""

from __future__ import annotations

import datetime as dt

import requests

from app.data import models as m
from app.data.db import session_scope

CVELIST_RAW_BASE = "https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves"
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
OSV_QUERY_URL = "https://api.osv.dev/v1/query"

_CVSS_KEYS = ("cvssV3_1", "cvssV3_0", "cvssV2")
_NVD_METRIC_KEYS = ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2")


def _cvelist_path(cve_id: str) -> str:
    # Layout: cves/<year>/<Nxxx>/<cve_id>.json, where <Nxxx> groups by the
    # sequence number's thousands digit(s) (e.g. CVE-2023-1234 -> 1xxx).
    _, year, seq = cve_id.split("-")
    bucket = f"{seq[:-3]}xxx" if len(seq) > 3 else "0xxx"
    return f"{CVELIST_RAW_BASE}/{year}/{bucket}/{cve_id}.json"


def _extract_cvss_from_metrics(metrics: dict | list) -> tuple[float, str] | None:
    """metrics is either the CNA-container's `metrics` list (CVE List V5
    schema) or one of its dict entries; returns (score, vector) for the
    highest-priority CVSS version found, or None."""
    if isinstance(metrics, dict):
        metrics = [metrics]
    for entry in metrics or []:
        for key in _CVSS_KEYS:
            block = entry.get(key)
            if block and block.get("baseScore") is not None:
                return float(block["baseScore"]), block.get("vectorString", "")
    return None


def fetch_cvelist_record(cve_id: str, timeout: float = 20.0) -> dict | None:
    url = _cvelist_path(cve_id)
    response = requests.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def fetch_nvd_cvss(cve_id: str, timeout: float = 20.0) -> tuple[float, str] | None:
    response = requests.get(NVD_API_URL, params={"cveId": cve_id}, timeout=timeout)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    vulns = payload.get("vulnerabilities") or []
    if not vulns:
        return None
    metrics = vulns[0].get("cve", {}).get("metrics", {})
    for key in _NVD_METRIC_KEYS:
        entries = metrics.get(key)
        if entries:
            cvss_data = entries[0].get("cvssData", {})
            if cvss_data.get("baseScore") is not None:
                return float(cvss_data["baseScore"]), cvss_data.get("vectorString", "")
    return None


def resolve_cvss_score(cve_id: str) -> tuple[float | None, str, str]:
    """Returns (score, vector, source) applying the CNA -> ADP -> NVD ->
    default precedence (build-spec.md / PLAN.md Task 14). `source` is one of
    "cna", "adp", "nvd", "default"."""
    record = fetch_cvelist_record(cve_id)
    if record:
        containers = record.get("containers", {})
        cna = containers.get("cna", {})
        found = _extract_cvss_from_metrics(cna.get("metrics", []))
        if found:
            return found[0], found[1], "cna"

        for adp_container in containers.get("adp", []):
            found = _extract_cvss_from_metrics(adp_container.get("metrics", []))
            if found:
                return found[0], found[1], "adp"

    found = fetch_nvd_cvss(cve_id)
    if found:
        return found[0], found[1], "nvd"

    return None, "", "default"


def enrich_cvss_scores(cve_ids: list[str] | None = None) -> dict:
    """Applies the precedence rule to every Vulnerability row (or a given
    subset). Logs its own INGEST_RUN. Never overwrites a row that already
    has a non-default score_source with a lower-precedence result -- refetch
    is idempotent, not regressive."""
    _PRECEDENCE_RANK = {"cna": 0, "adp": 1, "nvd": 2, "default": 3}

    with session_scope() as session:
        source = m.DataSource(
            name="CVE List V5 + Vulnrichment (CISA-ADP) + NVD",
            kind="api",
            licence_note="CVE List V5: CC0. NVD API: public, no auth required for low-volume use.",
        )
        session.add(source)
        session.flush()

        run = m.IngestRun(
            source_id=source.id,
            started_at=dt.datetime.now(dt.UTC),
            status="running",
        )
        session.add(run)
        session.flush()

        query = session.query(m.Vulnerability)
        if cve_ids is not None:
            query = query.filter(m.Vulnerability.cve_id.in_(cve_ids))
        vulns = query.all()

        n_updated = 0
        by_source = {"cna": 0, "adp": 0, "nvd": 0, "default": 0}
        errors: list[dict] = []

        for vuln in vulns:
            current_rank = _PRECEDENCE_RANK.get(vuln.score_source, 3)
            if current_rank < 3 and vuln.cvss_score is not None:
                # Already resolved at cna/adp/nvd tier; skip re-fetch.
                by_source[vuln.score_source] += 1
                continue
            try:
                score, vector, resolved_source = resolve_cvss_score(vuln.cve_id)
            except requests.RequestException as exc:
                errors.append({"cve_id": vuln.cve_id, "error": str(exc)})
                continue

            if score is not None:
                vuln.cvss_score = score
                vuln.cvss_vector = vector
            vuln.score_source = resolved_source
            by_source[resolved_source] += 1
            n_updated += 1

        run.finished_at = dt.datetime.now(dt.UTC)
        run.status = "completed"
        run.rows_in = len(vulns)
        run.rows_rejected = len(errors)
        run.rejection_log = {"errors": errors}

        return {
            "ingest_run_id": run.id,
            "n_checked": len(vulns),
            "n_updated": n_updated,
            "by_source": by_source,
            "n_errors": len(errors),
        }


def _osv_query_package(vendor: str, product: str, version: str, timeout: float = 15.0) -> list[dict]:
    """OSV keys advisories by ecosystem package name, not vendor/product, so
    a KEV vendor/product string (e.g. "Microsoft" / "Windows") is rarely a
    valid OSV package name. This queries OSV's purl-less `package.name`
    lookup on the product token alone as a best-effort match and returns
    whatever comes back -- confidence is scored by the caller, not assumed
    here."""
    body = {"version": version, "package": {"name": product}}
    response = requests.post(OSV_QUERY_URL, json=body, timeout=timeout)
    if response.status_code >= 400:
        return []
    return response.json().get("vulns", [])


def enrich_package_matches(limit: int | None = None) -> dict:
    """For each AssetSoftware row still carrying the L1
    'synthetic_no_inventory' placeholder, attempts an OSV/GitHub Advisories
    lookup on its Software's vendor/product/version and records a
    match_confidence: 1.0 for an exact version hit, 0.5 for a package-name
    hit with no version data to confirm, 0.0 (unchanged) for no hit at all.
    Because the synthetic assets carry fictitious versions, most lookups are
    honestly expected to return no match -- that is recorded, not hidden."""
    with session_scope() as session:
        source = m.DataSource(
            name="OSV.dev (package vulnerability matching)",
            kind="api",
            licence_note="OSV.dev API: public, CC-BY 4.0 data.",
        )
        session.add(source)
        session.flush()

        run = m.IngestRun(source_id=source.id, started_at=dt.datetime.now(dt.UTC), status="running")
        session.add(run)
        session.flush()

        query = (
            session.query(m.AssetSoftware)
            .filter(m.AssetSoftware.match_basis == "synthetic_no_inventory")
        )
        if limit is not None:
            query = query.limit(limit)
        rows = query.all()

        n_exact = 0
        n_partial = 0
        n_none = 0
        errors: list[dict] = []

        for row in rows:
            software = session.get(m.Software, row.software_id)
            if software is None:
                continue
            try:
                vulns = _osv_query_package(software.vendor, software.product, software.version)
            except requests.RequestException as exc:
                errors.append({"software_id": software.id, "error": str(exc)})
                continue

            if vulns and software.version != "unknown":
                row.match_confidence = 1.0
                row.match_basis = "osv_version_match"
                n_exact += 1
            elif vulns:
                row.match_confidence = 0.5
                row.match_basis = "osv_package_name_only"
                n_partial += 1
            else:
                row.match_basis = "osv_no_match"
                n_none += 1

        run.finished_at = dt.datetime.now(dt.UTC)
        run.status = "completed"
        run.rows_in = len(rows)
        run.rows_rejected = len(errors)
        run.rejection_log = {"errors": errors}

        return {
            "ingest_run_id": run.id,
            "n_checked": len(rows),
            "n_exact": n_exact,
            "n_partial": n_partial,
            "n_none": n_none,
            "n_errors": len(errors),
        }
