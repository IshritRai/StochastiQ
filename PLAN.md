# PLAN.md — StochastiQ, solo build (adapted from docs/build-spec.md)

## Context

`docs/build-spec.md` is a full, well-researched build spec for SIH PS 26105, but its build order, hour-sizing, and Section 2.3 team-stream table assume **6 people over 6 weeks (~700+ person-hours)**. The user is building **alone** and has explicitly overridden §2.3 and the weekly milestone table (per their prompt: "this prompt overrides those parts"). Everything else in the spec — schema, Risk Contract, guardrail tests, build-sequence *reasoning*, L1/L2/L3 ladder, and risk register — stands and is authoritative over my own preferences per the stated precedence (spec > research > my preferences).

I was not given an exact hour budget (the user answered "forget that" to my clarifying question), so this plan **assumes ~150–200 solo hours across 3–4 weeks part-time** as a working default — flagged explicitly as an assumption. If the real budget differs, the CUT LINE (§6) tells you exactly what to drop or add first; the task list's cumulative-hours column lets you re-truncate at whatever your actual ceiling is.

This is a **planning-only** deliverable: no application code is produced. Output is `PLAN.md` at the repo root plus this explanation.

---

## 1. Conflicts and things I will NOT silently resolve

Flagging per instruction, rather than picking silently:

1. **Team-size sections overridden by user, not by me.** Spec §2.3 (team streams) and the Week 1–6 milestone table assume 6 builders. Per explicit user instruction these are void; I've replaced them with a single serial task list (§4). The spec's *build-order reasoning* (§2.1) is kept as-is — it doesn't depend on team size.
2. **Problem statement vs. spec scope.** The original SIH problem statement (`docs/problem-statement.md`) asks for real ingestion from SIEM, IAM, EDR, CSPM. The build spec already narrows this to synthetic data + real CVE/KEV/EPSS feeds only, with a note that this is a deliberate scope reduction for a hackathon. I am carrying that reduction forward as-is — I'm not further shrinking it beyond what the spec already decided, but flagging that a judge who read only the problem statement may ask why there's no live SIEM/EDR connector. Suggested answer is already in the spec's "say this on stage" line (§4, R8) — use it.
3. **LLM vendor choice.** The spec and research talk about "an LLM" generically (OpenAI-style tool-calling) and never pick a vendor. The user's prompt fixes this: **Gemini API, called server-side only from the FastAPI backend, key in an environment variable.** This is new information not in the spec/research; I'm treating the user's runtime instruction as authoritative here since the spec is silent on vendor. No conflict, just noting the spec doesn't mention Gemini anywhere so there's no spec text to reconcile.
4. **CIS/FAIR-CAM licensing.** Spec already avoids FAIR-CAM (non-commercial license) and stores CIS/ISO as ID+short-title only. No conflict — carried forward unchanged.
5. **Currency/loss calibration numbers.** Spec explicitly invites me to propose better values for multiplier bounds, tail cap, and efficacy priors "as assumptions" — done in §7 below, not silently baked into code.
6. **Unresolved regulatory facts.** Spec §5 lists RBI paragraph numbers, SEBI circular numbers, and CSF subcategory IDs as unverified (sourced from secondary/third-party copies). I am **not** re-verifying these (no internet fetch was in scope for this planning pass) — they carry into Task 4 (compliance import) as open items to check against primary sources (rbi.org.in, sebi.gov.in, csrc.nist.gov) before the demo, per spec §5.

---

## 2. Task 0: repo scaffold

**Layout** (matches spec §2.2 contracts and §1 entity groups):

```
StochastiQ/
  app/
    api/            # FastAPI routers: scenarios, runs, attribution, optimize, compliance, nlq
    engine/         # simulate, summarize, run_scenario, run_org, attribute, apply_controls
    optimize/       # ROSI, knapsack (PuLP), budget curve
    compliance/      # framework import, mapping, status
    data/
      models.py      # SQLAlchemy ORM (Section 1 schema)
      seed/           # generator config + seed script
      ingest/         # CSV importer, KEV/EPSS/CVE fetchers
    nlq/            # intent router (L1), Gemini tool-calling (L2)
    config.py        # env-based config (DB URL, GEMINI_API_KEY, FX rate, seed)
  dashboard/
    Home.py           # Streamlit entry
    pages/            # Executive, Technical, What-if, Investment, Compliance
  tests/
    test_engine_guardrails.py   # R3 tests — written first, before engine code
    ... (mirrors app/ package layout)
  docs/                # existing, unchanged
  scripts/             # one-off maintenance/verification scripts
  Makefile             # seed / run / test / lint targets
  pyproject.toml       # or requirements.txt + requirements-dev.txt
  Dockerfile
  docker-compose.yml   # app + postgres, for the "cloud-ready" claim
  .github/workflows/ci.yml
  .gitignore
  README.md            # folder-structure explanation + how to run
```

**Makefile targets:** `make seed` (idempotent, same seed → same DB), `make run` (FastAPI + Streamlit together, or two targets `run-api`/`run-dashboard`), `make test` (pytest), `make lint`.

**CI:** GitHub Actions running `make test` on push; single Python version is fine solo (3.11+).

**Done when:** `make seed && make test` passes on a clean checkout; `README.md` explains every top-level folder in one line each.

*Est. 4h.*

---

## 3. Schema (spec §1, in full — no table dropped)

Implement every entity in spec §1.3 via SQLAlchemy, split by build tag exactly as the spec marks them:

- **All L1 tables now** (Task 1, below): ORGANIZATION, BUSINESS_UNIT, BUSINESS_SERVICE, ASSET_SERVICE, ASSET, SOFTWARE/ASSET_SOFTWARE, ACCOUNT, VULNERABILITY, FINDING, FINDING_RULE, CONTROL_TYPE, CONTROL_STATE, CONTROL_OPTION, THREAT_SCENARIO, SCENARIO_INPUT, SCENARIO_CONTROL_EFFECT, SIMULATION_RUN, RISK_ATTRIBUTION, INVESTMENT_PLAN/PLAN_ITEM, FRAMEWORK, FRAMEWORK_CONTROL, CONTROL_MAPPING, COMPLIANCE_STATUS, DATA_SOURCE/INGEST_RUN.
- **L2 tables created but left mostly empty/thin until their task:** INCIDENT/INCIDENT_LOSS, EVIDENCE, REPORTING_OBLIGATION.
- **L3 table stubbed only if time allows:** ASSET_DEPENDENCY.

Provenance fields (source, timestamp, run ID / inputs_hash / seed) are part of the schema from day one per CLAUDE.md rule 2 — not bolted on later.

*Est. 6h including migrations setup (Alembic optional; solo + SQLite can start with `create_all` and add Alembic only if a real migration is ever needed).*

---

## 4. Serial build order, one task per (mostly) Claude Code session

Hours are solo-focused estimates; "cum." = cumulative. Each task names its done-when test and, where applicable, keeps the spec's guardrail tests as a hard gate before downstream work starts (CLAUDE.md rule: "Tests before dependents build on a function").

| # | Task | Hours | Cum. | Done-when test | Session |
|---|---|---|---|---|---|
| 0 | Repo scaffold (§2) | 4 | 4 | `make seed && make test` runs clean on fresh checkout | 1 |
| 1 | Schema (§3) + tiny hand-written dataset (3 BUs, ~30 assets, 3 services, 8 scenarios) | 8 | 12 | Hand-seed script loads without FK errors; every table in §1.3 L1 list exists | 1 (can share with #0) |
| 2 | **R3 guardrail tests — written against a stub engine, before the real engine exists** | 4 | 16 | All 7 tests in spec §"R3...Guardrail tests" (fixed-freq×fixed-loss, lognormal percentile fit, seed reproducibility, org=Σscenario, zero-effect Δ=0, non-additive VaR, FAIR-U cross-check placeholder) are written and *fail* against a `NotImplementedError` stub — proves the tests are real, not tautological | 2 |
| 3 | Risk engine core: `simulate`, `summarize`, `run_scenario` (Risk Contract steps 1–5) | 14 | 30 | R3 tests 1–5 pass; 2 hand-picked scenarios reproduce FAIR-U/Open Group workbook within MC error (R3 test 7) | 2–3 |
| 4 | `run_org`, `attribute` (allocation method only, no leave-one-out yet) | 6 | 36 | R3 test 4 and test 6 pass; asset allocations sum to scenario EAL | 3 |
| 5 | Dashboard shell: 5 Streamlit pages reading the DB (Exec, Technical, What-if, Investment, Compliance — empty/placeholder where the backing engine task hasn't landed yet) | 8 | 44 | Every page loads without hard-coding a number; changing a DB row changes a page after rerun (CLAUDE.md rule 1) | 4 |
| 6 | Compliance spine: NIST CSF 2.0 import (JSON/Excel from CPRT), drop withdrawn 1.1 IDs, starter mapping (15–20 hand rows, flagged "starter, needs validation") | 10 | 54 | Fixing a finding flips its mapped subcategory gap→met; a test asserts no withdrawn CSF ID ever appears | 5 (parallel-in-spirit, but solo = sequential; can interleave with #3–4 if you want variety) |
| 7 | `apply_controls` primitive: mutate `CONTROL_STATE`/effects in memory, rerun `run_scenario` with the **same random draws** (common random numbers) | 6 | 60 | R3 test 5 (zero-effect Δ=0) passes through this primitive specifically, not just the raw engine | 6 |
| 8 | Real vuln intel + synthetic-company generator: CISA KEV JSON, FIRST EPSS, attach real CVE IDs to synthetic software inventory; latent per-BU maturity → correlated MFA/EDR/patch-latency; heavy-tailed asset/criticality; realistic missingness | 12 | 72 | `make seed` run twice gives byte-identical DB; removing a CVE's KEV flag changes its finding weight and downstream EAL (CLAUDE.md rule 1 acceptance test) | 7 |
| 9 | CSV importer (assets/findings/accounts) with validation, rejects logged to `INGEST_RUN` | 5 | 77 | Importing an edited CSV changes downstream figures; a malformed row is rejected and logged, not silently dropped | 7 |
| 10 | Decision support L1: scenario simulation (control-state sliders via `apply_controls`), mitigation recommendations (rank `CONTROL_OPTION` by ΔEAL/₹, template text) | 8 | 85 | ΔEAL/ΔVaR95 shown with P10–P90 range; every number in the templated text traces to a `RunResult` field, none invented | 8 |
| 11 | Optimizer L1: standalone ΔEAL per option via `apply_controls`, 0/1 knapsack (PuLP) under a budget, **joint re-simulation** of the chosen set, budget-sweep curve, Gordon-Loeb 37% flag | 10 | 95 | Zero-effect option → ΔEAL exactly 0; curve never decreases as budget grows (spec §3.4 done-when); joint result is shown next to the knapsack estimate, not hidden | 9 |
| 12 | NL interface L1: intent router (regex/keywords) over 8–10 intents → real functions, honest "can't answer" fallback | 6 | 101 | ~30 test questions (spec R5) run; every in-scope one hits a real function, every out-of-scope one gets the honest fallback, none invents a number | 10 |
| 13 | Wire dashboards to real engine/optimizer/compliance outputs (replace placeholders from #5); lakh/crore formatting function, tested | 8 | 109 | Every figure on every page traces to a run ID; a tested formatter never off-by-one on lakh/crore boundaries | 11 |
| **— M1-equivalent checkpoint: full demo path exists at L1 (spec §3.8's M1 row), all in one solo pass —** ||| |
| 14 | Enrich vuln intel to L2: CVE List V5 + Vulnrichment precedence rule (CNA→ADP→NVD→default), log source per score; OSV/GitHub Advisories package matching with match-confidence | 8 | 117 | A vulnerability's `score_source` field is populated and a test asserts the precedence order is honored | 12 |
| 15 | Telemetry-driven `ExposureMult` (bounded), tornado/sensitivity chart, Fragile/Unstable flags | 8 | 125 | A test proves extreme findings cannot move EAL beyond the configured bound (R1 guardrail) | 12 |
| 16 | Gemini LLM narrative + tool-calling upgrade to NL layer (L2): allow-listed function calling, code inserts all numbers, model only phrases text; run ID + source shown on every answer | 10 | 135 | A test asserts every number appearing in an LLM-generated answer string also appears in the structured tool-call result passed to it (R5 guardrail) | 13 |
| 17 | RBI 2026 Directions + SEBI CSCRF catalogues (hand-built, paragraph/standard IDs, `verified` flag, effective_date, retired instruments kept), incident-clock engine (DAKSH 6h, CERT-In 6h, SEBI 6h/24h/3d/7d/30d/75d, DPDP 72h gated on commencement date) | 10 | 145 | Feeding one detection timestamp produces all clocks correctly, including DPDP showing "not yet in force" before 13 May 2027 | 14 |
| 18 | Risk-to-compliance link (₹ EAL attributable to each unmet control); trend chart over stored runs; drill-down org→BU→asset→finding | 8 | 153 | Trend chart uses a fixed seed across snapshots (no seed-per-refresh noise, per R3 guardrail #7) | 15 |
| **— target checkpoint at ~150h (this plan's default budget): stop here, harden, rehearse —** ||| |
| 19 | *(stretch, only if hours remain)* Weekly synthetic snapshots (12 weeks) for real trend history; Gamma-Poisson frequency updating from incident history | 10 | 163 | — | 16 |
| 20 | *(stretch)* Interaction-aware greedy optimizer with uncertainty bands; risk-averse objective (VaR95 or tail-penalty) | 10 | 173 | — | 17 |
| 21 | Demo hardening: frozen seed data, offline fallback if KEV/EPSS/Gemini unreachable, Docker image, README/architecture note, rehearsal, recorded backup video | 10 | 183 | `docker compose up` reproduces the exact demo state with no internet | 18 |

*(Tasks 19–20 are explicitly optional stretch and are the first things to cut if the real budget is under ~150h; see §6.)*

---

## 5. Every component present at L1 first, then L2 in demo-value order

Confirmed by the task table above — no component skips L1. The L2 pass order (tasks 14→18) follows spec §3.7's demo-value logic: exposure/telemetry realism and LLM tool-calling first (highest "wow" and highest R1/R5 risk if skipped), then Indian regulatory depth (RBI/SEBI — judges from AICTE/Indian context will probe this), then trend/drill-down polish last.

---

## 6. CUT LINE (explicit)

If real hours run short of the ~150h default:

**Cut first (in this order), never touch L1 correctness:**
1. Task 20 (interaction-aware optimizer, uncertainty bands) — L1 knapsack + joint re-sim already satisfies the spec's done-when test.
2. Task 19 (12-week snapshots, Gamma-Poisson updating) — a single-snapshot trend line with a "linear extrapolation" label (spec's L1 predictive-analytics option) substitutes.
3. Task 18's drill-down UI polish — keep the risk-to-compliance ₹ link (it's the spec's stated differentiator: "This is what makes the platform more than a checklist"), drop fancy drill-down navigation, use plain filtered tables instead.
4. Task 17's incident-clock engine can thin to RBI+CERT-In+SEBI only, dropping DPDP (it isn't even in force until 13 May 2027, so its demo value is lowest).
5. Task 16 (Gemini tool-calling) can fall back to Task 12's regex intent router only, with Gemini used solely for narrative phrasing of Task 10's recommendation text (still real, still guarded, just no dynamic function selection).

**Never cut, whatever the budget:** Task 2 (R3 guardrails), Task 3–4 (engine core), Task 7 (`apply_controls` with common random numbers), Task 11's joint re-simulation, and the "no hard-coded outputs" / provenance rules from CLAUDE.md — these are what make the platform's numbers trustworthy rather than a themed calculator, and every downstream L2/L3 item depends on them being solid.

**Which L1s can be thinner than the spec's own L1 if truly squeezed:**
- Compliance mapping (Task 6): 8–10 rows instead of 15–20, still flagged "starter."
- Synthetic generator (Task 8): drop the correlated missingness realism (stale last-seen, blank owners) — keep the maturity→control-coverage correlation, which is the load-bearing part for control-effectiveness demos.
- NL interface (Task 12): 5–6 intents instead of 8–10, but keep the honest-fallback behavior — an NL box that fakes confidence is worse than fewer intents.

---

## 7. Proposed values for multiplier bounds, tail cap, efficacy priors (assumptions — mark and revisit)

The spec invites better values here; these are proposals, not facts, and must be labeled `is_assumption=true` in the DB per the schema's own field for this:

- **ExposureMult bounds:** `clip(index_t / index_baseline, 0.5, 3.0)`. Rationale: allows exposure to roughly triple under a KEV-heavy backlog or halve under strong patching, without letting one finding blow past a plausible range (guards R1's "EAL swings when one CVE appears" symptom). Revisit once you have >1 snapshot of real data.
- **Tail cap:** cap individual event loss at a documented multiple of `BUSINESS_SERVICE.revenue_per_hour × 8760` (i.e., cannot exceed one year of the affected service's full revenue) — a hard, explainable ceiling rather than an arbitrary rupee figure. Combine with the lognormal σ≈2.4 implied by Cyentia IRIS 2025 (median $600K, P95 $32M) from the loss-calibration research, and note IRIS is a *global, publicly-reported* population being used as a shape proxy for an Indian synthetic firm — label as illustrative per spec §1.4.
- **Combined control reduction cap:** cap the product of `(1 − coverage×efficacy)` terms across all resistive controls on one scenario at a floor of 0.15 (i.e., controls can never jointly claim more than an 85% Vuln reduction) — directly implements the R1 guardrail ("cap on combined control reduction") the spec calls for without specifying a number.
- **Efficacy priors (all `is_assumption=true`, PERT low/mode/high, since the research found no verified public source):**
  - MFA (resistive, PR.AA): 0.60 / 0.80 / 0.95
  - EDR (resistive): 0.40 / 0.65 / 0.85
  - Network segmentation (avoidance, changes CF): 0.30 / 0.55 / 0.75
  - Patch/vuln management (resistive): 0.35 / 0.60 / 0.85
  - SIEM/monitoring (responsive, changes SLEF/PLM): 0.20 / 0.45 / 0.70
  These are my proposals for plausible, defensible ranges given the research explicitly found no calibrated source — present them on stage as assumptions with a tornado chart, exactly as spec R1 recommends, never as measured facts.
- **FX rate:** single configurable value in `config.py`, sourced from a stated date, labeled illustrative wherever a converted ₹ figure appears (spec §1.4, R2).

---

## 8. Open questions, assumptions, and unverified facts carried from spec §5

Not re-verified in this planning pass (no live fetch was needed for planning); carry into Task 8 (feeds) / Task 17 (regulatory) as pre-demo checks:

1. NVD "Not Scheduled" CVE count and any NVD announcement after the 13 Oct 2026 RFI close.
2. Current CISA KEV count (count the JSON at build time) and any BOD 26-04 changes.
3. EPSS model version, bulk file host (cyentia.com vs empiricalsecurity.com — both should be tried), and rate limits.
4. RBI 2026 Directions paragraph numbers (151, 165, 182, 230) and the repeal annex — checked in research only against a third-party copy, not rbi.org.in directly. Same for the SEBI FIRE circular reference (24 Aug 2026, secondary-sourced only).
5. Every specific CSF subcategory ID and CIS safeguard number used in the starter compliance mapping (Task 6), and ISO Annex A titles, against ISO OBP / CPRT directly.
6. IBM 2026 and NetDiligence 2026 headline loss figures — pull from the actual PDFs before quoting them in any UI copy, not from blog summaries.
7. Licenses of any third-party repo reused (pyfair, riskquant, evaluator, adsimulator, BOTS) — check LICENSE files at the commit you actually pin, not from memory.
8. **New (not in spec, from this session):** Gemini API model/tier availability and rate limits under the environment's actual key — verify before Task 16, since the NL layer's fallback behavior (Task 12) needs to degrade gracefully if the Gemini call fails or is rate-limited.

---

## 9. Fixed elements confirmed, not up for renegotiation

Per the user's prompt, these are locked and every task above respects them:
- Risk Contract structure exactly as spec §1.4 (baseline inputs → exposure adjustment → control adjustment → simulate → summarize → aggregate → attribute).
- Per-scenario computation with downward attribution (never sum VaR across scenarios/BUs/assets — sum loss vectors first, then take percentiles).
- Joint re-simulation of chosen investment plans (Task 11) — the standalone/joint gap is treated as a feature to display, not an error to hide.
