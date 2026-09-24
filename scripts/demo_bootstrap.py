"""One-shot demo bootstrap (PLAN.md Task 21: demo hardening).

Builds the exact same demo state every time, with or without internet:
1. `seed()` -- synthetic company + frameworks + starter compliance mapping.
   Fully offline already (no network calls; CLAUDE.md rule 1's "same seed,
   same data" guarantee).
2. `import_vuln_intel()` -- real CISA KEV + FIRST EPSS data. Tries the live
   feeds first; falls back to the frozen fixture in app/data/fixtures/ on
   any network failure, so this step always succeeds (see
   app/data/ingest/vuln_intel.py and app/data/fixtures/README.md).
3. `enrich_cvss_scores()` / `enrich_package_matches()` -- best-effort L2
   enrichment (CVE List V5 / NVD / OSV). These already catch per-row
   network errors and log them to INGEST_RUN.rejection_log rather than
   raising, so a fully offline run just leaves those rows unenriched
   instead of failing the bootstrap.

This is what `docker compose up` runs before the API/dashboard start, so a
judge on conference wifi (or with no internet at all) gets the identical
demo dataset every time (Task 21 done-when: "docker compose up reproduces
the exact demo state with no internet").
"""

from __future__ import annotations

from app.data.ingest.cve_enrich import enrich_cvss_scores, enrich_package_matches
from app.data.ingest.vuln_intel import import_vuln_intel
from app.data.seed.seed import seed


def main() -> None:
    print("[demo-bootstrap] seeding synthetic company...")
    seed()

    print("[demo-bootstrap] attaching real CISA KEV / FIRST EPSS data...")
    vuln_result = import_vuln_intel()
    print(
        f"[demo-bootstrap]   kev_source={vuln_result['kev_source']} "
        f"epss_source={vuln_result['epss_source']} "
        f"n_created_vulns={vuln_result['n_created_vulns']}"
    )

    print("[demo-bootstrap] enriching CVSS scores (best-effort, may skip offline)...")
    cvss_result = enrich_cvss_scores()
    print(f"[demo-bootstrap]   n_updated={cvss_result['n_updated']} n_errors={cvss_result['n_errors']}")

    print("[demo-bootstrap] matching packages against OSV (best-effort, may skip offline)...")
    pkg_result = enrich_package_matches()
    print(f"[demo-bootstrap]   n_exact={pkg_result['n_exact']} n_errors={pkg_result['n_errors']}")

    print("[demo-bootstrap] done.")


if __name__ == "__main__":
    main()
