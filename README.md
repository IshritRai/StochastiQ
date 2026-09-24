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

make seed          # builds the synthetic demo company (idempotent: same seed, same data)
make test          # runs the guardrail + seed test suite
make run-api        # FastAPI on :8000
make run-dashboard   # Streamlit on :8501
```

Or via Docker: `docker compose up` (Postgres + API + dashboard).

## Current status

`PLAN.md` Tasks 0–5 are done: repo scaffold, full database schema, a
hand-written synthetic seed dataset (with controls linked to the scenarios
they affect), the real Monte Carlo engine (`simulate`/`summarize`/
`run_scenario`/`run_org`/`attribute`/`apply_controls`), and a 5-page
Streamlit dashboard (Executive, Technical, What-if, Investment, Compliance)
reading live from the database. `make seed && make test` passes; `make
run-dashboard` shows real EAL/VaR/loss-exceedance figures for the synthetic
demo company. The Investment and Compliance pages are intentionally
placeholders until their backing engine work (Tasks 6 and 11) lands — they
show no fabricated numbers in the meantime.

See `PLAN.md` for the full task-by-task order, the cut line, and the
proposed assumption values (multiplier bounds, tail cap, control efficacy
priors) still awaiting real telemetry or verified public sources.
