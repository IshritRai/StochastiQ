# L1 verification: perturbation checks

The automated guardrail suite (`tests/test_engine_guardrails.py`)
proves the engine's math is internally consistent. It does NOT prove the real,
running dashboard shows consistent numbers across pages, because each page
wires the engine together slightly differently (which seed it passes, how it
builds `overrides`, what it does with the resulting `loss_vector`). The way
these are actually found is by perturbing the live app: changing a seed, moving a slider back to where it started, comparing two pages that should agree, and checking the numbers, not by re-reading the code.

Two real bugs were caught this way. Both are pinned as permanent automated
tests (`tests/test_perturbation_checks.py`) so they can never silently
regress. Recorded here so the fix and its reasoning survive independent
of the commit that made it.

## 1. Executive vs. What-if disagreeing on the same scenario's EAL

**Symptom:** the same scenario, same seed=42, showed EAL=₹4.99 L on the
Executive page (via `run_org`) and EAL=₹4.48 L on the What-if page (via
`run_scenario`): a ~10% disagreement with no override in play.

**Root cause:** `run_org_impl` derived a per-scenario seed via
`_derive_seed(seed, scenario_id)` before calling `run_scenario_impl`, so that
scenarios inside one org run draw independent random numbers from each other
(correct: scenarios must be independent). But `run_scenario_impl`,
called directly (e.g. from the What-if page), used the raw seed with no
derivation. The two call paths therefore used two DIFFERENT effective seeds
for the identical scenario, so two independently-correct draws of the same
distribution disagreed by ordinary Monte Carlo noise: small, but real and
visible at the precision the UI displays.

**Fix (`app/engine/risk_contract.py`):** seed derivation moved INSIDE
`run_scenario_impl` itself: it is now the one shared seeding function. Every
caller (`run_scenario`, `apply_controls`, and each per-scenario call inside
`run_org`) passes the same caller-facing seed straight through;
`run_scenario_impl` always derives `_derive_seed(seed, scenario_id)`
internally before simulating. This guarantees, by construction, that
`run_scenario(sid, seed=S)` and `run_org(seed=S).scenario_results[sid]` are
byte-identical for the same `sid`/`S`/overrides, while still keeping
different scenarios independent of each other inside one org run.

**Permanent test:** `test_run_org_matches_run_scenario_for_same_seed` in
`tests/test_perturbation_checks.py`: asserts EAL, VaR95, and the full
loss vector are identical between the two call paths for the same scenario
and seed.

## 2. What-if's untouched slider showing a nonzero delta

**Symptom:** opening the What-if page and changing nothing (every slider left
at its own displayed default) showed a "What-if EAL" delta of +₹113, not
exactly 0, violating the requirement that a zero-effect override give
delta-EAL exactly 0.

**Root cause:** a `st.slider` is integer-valued (0-100), so its default is
`round(measured_coverage * 100)`: a true measured coverage of
66.666...% becomes a default of 67. The page then always converted the
slider's *current* value back to a fraction (`67 / 100.0 = 0.67`) and sent it
to `apply_controls` as an override, on every render, even when the user never
touched the slider. `apply_controls` has no way to tell "the user explicitly
chose 0.67" from "this is just the rounded baseline". It applied 0.67 where
the true baseline used 0.6667, a real (if tiny) coverage change, hence a
nonzero delta.

**Fix (`dashboard/whatif_logic.py`, used by `dashboard/views/3_What_if.py`):**
`build_overrides(slider_values, slider_defaults)` only includes a control in
the returned overrides dict if its current slider value differs from its own
rounded default. An untouched slider sends NO override for that control at
all, so `apply_controls` falls back to computing the measured coverage
exactly the same way the baseline run did, giving delta = 0 exactly, not
approximately.

**Permanent test:** `test_untouched_slider_gives_exactly_zero_delta` in
`tests/test_perturbation_checks.py`: uses a coverage value (2/3) whose
rounded slider default does NOT equal the exact measured value, runs
`build_overrides` on an untouched slider, and asserts the resulting
`apply_controls` run is byte-identical to the baseline `run_scenario` run.

## Process note

Both of these were caught by manually perturbing the running app (changing a
seed, resetting a slider) and comparing pages that are supposed to agree,
not by rereading the code or by the pre-existing automated suite, which
passed 100% both times. This is the same lesson recorded earlier in this
project's history for the `dashboard` packaging bug: **passing tests are
necessary, not sufficient: perturb the real, running app and check that
things which should match actually do.** New engine or dashboard-wiring
changes should get at least one such perturbation check before being called
done, in addition to their unit tests.
