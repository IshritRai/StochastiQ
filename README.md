# StochastiQ

AI-powered continuous cyber risk quantification and investment optimization
platform. See `docs/problem-statement.md`, `docs/build-spec.md`, and
`docs/research/` for the full design background.

**Company data is synthetic. The Monte Carlo math, the vulnerability
intelligence (KEV/EPSS/CVE), and the framework catalogues (NIST CSF, ISO,
CIS, RBI, SEBI) are real.**

## Folder structure

- `app/api/`: FastAPI routers. Thin: they call into `app/engine` and friends, no business logic.
- `app/engine/`: the Risk Quantification Engine (`simulate`, `summarize`, `run_scenario`, `run_org`, `attribute`, `apply_controls`). Imported as a plain Python library by both the API and the dashboard, no microservices.
- `app/optimize/`: ROSI calculation and the 0/1 knapsack investment optimizer (PuLP), plus the budget-sweep curve.
- `app/compliance/`: framework import (NIST CSF 2.0 etc.), finding-to-control mapping, compliance status computation.
- `app/data/`: SQLAlchemy models (`models.py`), DB session wiring (`db.py`), the synthetic-company seed generator (`seed/`), and CSV/feed importers (`ingest/`).
- `app/nlq/`: the natural-language query layer, an intent router first, then Gemini tool-calling.
- `app/config.py`: all environment-based configuration (DB URL, Gemini API key, FX rate, simulation defaults, assumption bounds). Nothing here is a secret checked into source.
- `dashboard/`: the Streamlit app. `Home.py` is the `st.navigation` shell (page config, shared stylesheet, sidebar brand, and the sectioned nav itself: Overview / Risk / Decisions); `views/` holds each page's actual content (Home, Executive, Technical, What-if, Investment, Compliance), rendered by `nav.run()`.
- `tests/`: pytest suite, including `test_engine_guardrails.py`, the guardrail tests written before the engine they guard.
- `docs/`: the project's design documents (spec, research, problem statement).
- `scripts/`: one-off maintenance or verification scripts, and the demo bootstrap used by Docker.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

make seed              # builds the synthetic demo company (idempotent: same seed, same data)
make fetch-vuln-intel  # pulls the live CISA KEV catalog + FIRST EPSS scores (real, not synthetic)
make test              # runs the guardrail + seed test suite
make run-api            # FastAPI on :8000
make run-dashboard      # Streamlit on :8501
```

Or via Docker: `docker compose up` (Postgres, a one-shot `init` bootstrap,
API, and dashboard). `init` runs `scripts/demo_bootstrap.py`: seed, then
KEV/EPSS ingestion, then best-effort CVSS/OSV enrichment, building the
identical demo dataset **with or without internet access**. KEV/EPSS try
the live feeds first and fall back to the frozen snapshot in
`app/data/fixtures/` on any network failure (see that folder's README).
`api`/`dashboard` wait for `init` to finish before starting, so there is no
"dashboard is up but the database is empty" race.

## What it does

- **Risk quantification**: a Monte Carlo engine (`simulate`/`summarize`/
  `run_scenario`/`run_org`/`attribute`/`apply_controls`) computes Expected
  Annual Loss and Value-at-Risk per threat scenario, then aggregates and
  attributes risk downward to business units, assets, and findings, never
  by summing VaR across scenarios.
- **Executive, Technical, What-if, Investment, and Compliance dashboards**,
  all reading live from the same database and the same run contract; no
  page hard-codes a number.
- **Real vulnerability intelligence**: CISA KEV and FIRST EPSS ingestion,
  CVE List V5 + Vulnrichment (CISA-ADP) CVSS-score precedence (CNA to ADP
  to NVD to default), and OSV.dev package-version matching, each logged
  with its own source, timestamp, and run ID.
- **Telemetry-driven exposure**: `ExposureMult` is computed from currently
  open findings (KEV membership and EPSS both weigh a finding more
  heavily), clipped to a configured bound so no single extreme finding can
  swing EAL past it. The Technical page shows a tornado/sensitivity chart
  and Fragile/Unstable stability flags per scenario.
- **Natural-language query layer**: an intent router over a fixed set of
  real engine/database calls, with allow-listed Gemini tool-calling for
  phrasing only (the model never computes a number). Every numeric token
  in the model's answer is checked against the structured tool result
  before being shown; any mismatch or Gemini failure falls back to the
  code-generated sentence.
- **Investment optimization**: standalone ROSI per control, a 0/1 knapsack
  under a budget (PuLP), and a joint re-simulation of the chosen set shown
  alongside the knapsack's additive estimate, since the gap between them
  is itself informative when controls interact.
- **Compliance**: the full NIST CSF 2.0 catalog (all 106 subcategories,
  from NIST's own public-domain OSCAL data), a starter finding-to-control
  mapping, hand-built RBI 2026 Cybersecurity Directions and SEBI CSCRF
  catalogues (paragraph/standard IDs and short titles only, verified
  against primary sources), an incident-clock calculator (DAKSH, CERT-In,
  SEBI, DPDP), and a risk-to-compliance rupee link that allocates a run's
  EAL across every unmet control.
- **Demo hardening**: a frozen, real KEV/EPSS snapshot as an offline
  fallback for the live feeds, and a one-shot Docker bootstrap so
  `docker compose up` reproduces the same demo dataset with or without
  internet access.

See `docs/build-spec.md` for the full design rationale, the Risk Contract,
and the proposed assumption values (multiplier bounds, tail cap, control
efficacy priors) still awaiting real telemetry or verified public sources.
