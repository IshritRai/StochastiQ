# StochastiQ

AI-powered continuous cyber risk quantification and investment optimization
platform for SIH Problem Statement 26105. See `docs/problem-statement.md`,
`docs/build-spec.md`, `docs/research/`, and `PLAN.md` (the solo-builder task
list adapted from the build spec) for the full design.

**Company data is synthetic. The Monte Carlo math, the vulnerability
intelligence (KEV/EPSS/CVE), and the framework catalogues (NIST CSF, ISO,
CIS, RBI, SEBI) are real.**

## Folder structure

- `app/api/` — FastAPI routers. Thin: they call into `app/engine` and friends, no business logic.
- `app/engine/` — the Risk Quantification Engine: `simulate`, `summarize`, `run_scenario`, `run_org`, `attribute`, `apply_controls`. Imported as a plain Python library by both the API and the dashboard — no microservices.
- `app/optimize/` — ROSI calculation and the 0/1 knapsack investment optimizer (PuLP), plus the budget-sweep curve.
- `app/compliance/` — framework import (NIST CSF 2.0 etc.), finding-to-control mapping, compliance status computation.
- `app/data/` — SQLAlchemy models (`models.py`, implementing `docs/build-spec.md` section 1 in full), DB session wiring (`db.py`), the synthetic-company seed generator (`seed/`), and CSV/feed importers (`ingest/`).
- `app/nlq/` — the natural-language query layer: an intent router first (L1), then Gemini tool-calling (L2).
- `app/config.py` — all environment-based configuration (DB URL, Gemini API key, FX rate, simulation defaults, assumption bounds). Nothing here is a secret checked into source.
- `dashboard/` — the Streamlit app: `Home.py` plus `pages/` for Executive, Technical, What-if, Investment, and Compliance views.
- `tests/` — pytest suite, including `test_engine_guardrails.py`, the R3 guardrail tests from `docs/build-spec.md`, written before the engine they guard.
- `docs/` — the project's design documents (spec, research, problem statement) and this plan's source material.
- `scripts/` — one-off maintenance or verification scripts (e.g. re-checking a regulatory fact before a demo).

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

make seed             # builds the synthetic demo company (idempotent: same seed, same data)
make fetch-vuln-intel  # pulls the live CISA KEV catalog + FIRST EPSS scores (real, not synthetic)
make test             # runs the guardrail + seed test suite
make run-api           # FastAPI on :8000
make run-dashboard      # Streamlit on :8501
```

Or via Docker: `docker compose up` (Postgres + API + dashboard).

## Current status

`PLAN.md` Tasks 0–12 are done: repo scaffold, full database schema, the
synthetic seed generator, the real Monte Carlo engine (`simulate`/
`summarize`/`run_scenario`/`run_org`/`attribute`/`apply_controls`), a
5-page live Streamlit dashboard, the full NIST CSF 2.0 catalog (all 106
subcategories, from NIST's own public-domain OSCAL data) with a starter
compliance mapping, a CSV importer, real CISA KEV + FIRST EPSS ingestion
(`make fetch-vuln-intel` — live data, not synthetic), the investment
optimizer (ROSI, knapsack, joint re-simulation), KEV-first remediation
recommendations, and a 9-intent natural-language query router.
`make seed && make fetch-vuln-intel && make test` passes end to end.

Task 14 is also done: CVE List V5 + Vulnrichment (CISA-ADP) CVSS-score
precedence (CNA → ADP → NVD → default, `make enrich-vuln-intel` — live
data), logged per-`Vulnerability.score_source`, plus OSV.dev package-version
matching with a `match_confidence` on `AssetSoftware` (honestly 0 for the
synthetic inventory's placeholder software, since it carries no real
versions to match against).

Task 16 is also done: the NL router now tries allow-listed Gemini
tool-calling first when `GEMINI_API_KEY` is set (`app/nlq/gemini_client.py`,
`app/nlq/llm_router.py`) — Gemini may only pick an intent name from the same
fixed set Task 12's regex router uses, and phrase the final sentence; it
never computes a number. Every numeric token in the model's phrasing is
checked against the structured tool-call result before being shown
(`tests/test_nlq_llm.py`, the R5 guardrail); a mismatch, a missing/invalid
key, or any Gemini failure falls straight back to the code-generated
sentence, so the 9 intents behave the same with or without a key.

Task 15 is also done: ExposureMult is now telemetry-driven
(`app/engine/exposure.py`) instead of the L1 identity 1.0 — it is computed
from currently-open findings (KEV membership and EPSS both weigh a finding
more heavily), and clipped to `[exposure_mult_lo, exposure_mult_hi]` so no
single extreme finding can swing EAL past that configured bound
(build-spec.md risk R1; the guardrail test,
`tests/test_exposure_guardrail.py`, was written and run to fail before this
was implemented, per CLAUDE.md). The Technical page now shows, per
scenario: the clipped ExposureMult (flagged when the raw telemetry value
was clipped), a tornado/sensitivity chart perturbing each Risk Contract
factor by ±20% with common random numbers, and Fragile/Unstable stability
flags.

Task 17 is also done: hand-built RBI 2026 Cybersecurity Directions + SEBI
CSCRF catalogues (`app/compliance/rbi_sebi_data.py`, paragraph/standard IDs
and short titles only) and the incident-clock engine
(`app/compliance/incident_clock.py` — DAKSH 6h, CERT-In 6h, SEBI 6h/24h/
3d/7d/30d/75d, DPDP 72h gated on its 13 May 2027 commencement date). Every
row is honestly `verified=False`: researched via secondary sources in this
pass (WebSearch over legal/industry commentary), not confirmed against
rbi.org.in or sebi.gov.in directly — shown as an unverified badge on the
Compliance page rather than silently promoted. The Compliance page's new
"Incident-Clock Calculator" turns one detection timestamp + entity type
into every applicable deadline, live from the DB.

Still open: Task 18 (risk-to-compliance ₹ link, trend chart, drill-down)
and demo hardening (Task 21) are next.

See `PLAN.md` for the full task-by-task order, the cut line, and the
proposed assumption values (multiplier bounds, tail cap, control efficacy
priors) still awaiting real telemetry or verified public sources.
