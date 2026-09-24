# R2 frequency-anchor check and control-cost source audit

Per build-spec.md risk R2's guardrail ("a check that summed scenario
frequencies are consistent with the segment's all-event anchor") and the
instruction to report this honestly rather than silently tune values to
force a particular ROSI outcome.

## 1. Summed scenario base frequencies vs. the segment anchor

`app/data/seed/seed_config.py`'s module docstring states the intent: "Coalition's
1.54% all-event claims rate as a segment anchor... each scenario gets a
fraction of it, so that summed scenario frequencies stay consistent with the
segment's all-event anchor."

Measured directly from the 8 `ThreatScenarioSpec.tef` ranges (`low, mode, high`,
events/year):

| | low | mode | high |
|---|---|---|---|
| **Sum across all 8 scenarios** | 0.76 | **1.62** | 3.13 |
| **Segment anchor (Coalition all-event claims rate)** | | **0.0154** | |
| **Ratio, mode vs. anchor** | | **~105x** | |

**This does not check out.** The summed scenario TEF *mode* (1.62 events/year)
is about 105x the stated 1.54%-probability-of-any-claim anchor, not "a
fraction of it." I do not have a verified secondary source stating what
Coalition's 1.54% figure actually measures beyond what's already cited in
`docs/research/loss-caliberation.md` (I have not re-read that file's exact
wording in this pass), but at face value a 1.54% figure reads as an annual
probability of at least one claim, not an expected count of ~1.6 events/year
-- those are different anchors from the start (probability-of-any-event vs.
expected-count) and doing this rescaling would matter for both what
"consistent with the anchor" should mean and for what fraction each scenario
should carry. I'm flagging this rather than reconciling it myself: the
per-scenario TEF ranges were set individually per-scenario against each
scenario's own calibration_source (mostly Coalition per-category averages),
not derived arithmetically from the 1.54% figure, so the docstring's claim
that they were built to sum consistently with it does not appear to hold as
currently seeded.

**I have not changed any TEF value.** Rescaling 8 hand-set ranges to hit a
target sum is exactly the kind of change build-spec.md and CLAUDE.md ask me
not to make unilaterally when it would move every downstream EAL/ROSI number;
it needs a decision about which anchor definition to hold fixed. Proposed
options, both requiring `is_assumption=True` and a rationale note per row:
- (a) Scale every scenario's TEF range down by a common factor so the sum of
  modes lands at a chosen fraction of 0.0154 (e.g. treating 1.54% as itself
  representing "any claim," and estimating that within a given year a firm
  like this synthetic one might have on the order of 1 in 10 to 1 in 3 of the
  claim types modeled here actually fire) -- but I do not have a verified
  public source for that further breakdown, so it would carry its own
  `is_assumption=True` on top of the existing one.
- (b) Keep the current per-scenario Coalition/DBIR-sourced TEF ranges as-is
  and drop the docstring's "sums consistent with the anchor" claim, since
  each range already has its own cited calibration_source and the anchor
  check was aspirational rather than actually enforced at seed time.

I'd recommend (b) as the smaller, more honest change (fix the doc claim, not
the data) unless there's a reason to want the composite-anchor property for
the demo narrative, but this is a product call, not mine to make silently.

## 2. Control cost sources

`app/data/seed/seed.py::_make_control_options` sets, for every `ControlType`:

```python
capex=float(rng.uniform(500_000, 5_000_000)),        # INR
opex_per_year=float(rng.uniform(100_000, 1_000_000)), # INR
```

**There is no calibration source for these ranges at all** -- no citation, no
`is_assumption` field on `ControlOption` (the model's docstring says "Costs
are user-editable assumptions" but nothing marks or dates that assumption the
way `ScenarioInput.calibration_source`/`rationale`/`is_assumption` do for the
risk factors), and the values are independent random draws per control type,
not sourced from any published security-spend benchmark. I do not have a
verified, named source (report, vendor pricing page, or benchmark study) for
what MFA, EDR, network segmentation, patch management, or SIEM/monitoring
actually cost an Indian mid-market NBFC per year, and I am not going to
invent one -- per the "no hard-coded outputs... provenance on every number"
rule, this is a real gap, not a resolved item.

**Practical consequence, observed directly (`make seed && make fetch-vuln-intel`,
seed=42):** every one of the 5 standalone control options currently shows
**negative ROSI** (-77% to -99%), i.e. the randomly-drawn annualized cost
exceeds the standalone ΔEAL for all 5 options at this seed. This is a
legitimate result of the current (uncited) cost draws combined with the
current (partially-checked, see §1) frequency calibration -- not a bug, and
I have not adjusted anything to flip it positive, per the explicit
instruction not to tune values to force positive ROSI.

**Proposed fix (not yet applied):** add a `cost_source` (or reuse a new
`prior_source`/`is_assumption` pair, mirroring `ScenarioInput`) field to
`ControlOption`, and replace the raw `rng.uniform` draws with named,
labeled-assumption ranges the same way `ControlType.efficacy_*` already
carries `prior_source="PLAN.md section 7 (no verified public efficacy source
found; assumption)"`. Until a real vendor-pricing or industry-benchmark
source is found and cited, the honest label for the current cost numbers is
"illustrative, uncalibrated assumption," not "measured."
