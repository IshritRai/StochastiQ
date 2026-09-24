# Frozen demo fixtures

`kev_snapshot.json` and `epss_snapshot.json` are a real, one-time capture of
the live CISA KEV catalog and FIRST EPSS API, restricted to the exact 15
KEV entries that `import_vuln_intel(seed=<default_seed>)` samples with the
project's default seed. They are **not synthetic**: every CVE ID, vendor,
product, EPSS score and percentile in these files is genuine data pulled
from the real feeds.

They exist solely as an **offline fallback** for `make fetch-vuln-intel` /
`import_vuln_intel()` when `https://www.cisa.gov` or `https://api.first.org`
are unreachable (a restricted network, an air-gapped environment, or
`docker compose up` with no internet at all). `app/data/ingest/vuln_intel.py`
always tries the live feeds first; it only reads these files after both live
calls fail, and it records `kev_source="offline_fixture"` /
`epss_source="offline_fixture"` on the resulting `IngestRun.rejection_log`
so the provenance trail is honest about which run was live vs. frozen.

Captured: 2026-09-24, from the live CISA KEV feed (`catalogVersion`
"2026.09.23") and the live FIRST EPSS API. Re-capture by running, with
internet access:

```
python -c "from app.data.ingest.vuln_intel import refresh_offline_fixture; refresh_offline_fixture()"
```
