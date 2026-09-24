"""Event-level Monte Carlo simulation and summary statistics.

Implements build-spec.md section 1.4 steps 4-5 (simulate, summarize) and the
per-iteration algorithm from docs/research/fair-based-cyber-risk.md:

    1. Sample TEF (or CF x PoA).
    2. Sample Vuln (post exposure/control adjustment, done by the caller).
    3. N ~ Poisson(TEF x Vuln) events for the year.
    4. Each event draws a primary loss; with probability SLEF, also a
       secondary loss. Sum per iteration, then cap at the tail cap.

Event-level (not "one frequency draw x one loss draw") because a single
sampled frequency times a single sampled loss understates variance when
frequency exceeds 1 (build-spec.md risk R3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from app.engine.sampling import sample_loss_magnitude, sample_pert

if TYPE_CHECKING:
    from app.engine.contracts import SummaryResult


def simulate(inputs: dict, seed: int, n_iter: int) -> np.ndarray:
    """Run the event-level Monte Carlo and return the annual-loss vector.

    `inputs` keys:
      - "tef": scalar or {low, mode, high} -- Threat Event Frequency.
      - "vuln": scalar or {low, mode, high} -- Vulnerability (0..1), already
        adjusted for exposure/controls by the caller (run_scenario/apply_controls).
      - "plm_fixed" | ("plm_p05", "plm_p95") | "plm": primary loss magnitude.
      - "slef": scalar or {low, mode, high} -- probability of a secondary loss.
      - "slm_fixed" | ("slm_p05", "slm_p95") | "slm": secondary loss magnitude
        (only sampled for events that trigger a secondary loss; omit entirely
        to model no secondary loss).
      - "tail_cap": optional scalar; per-iteration annual loss is truncated here.

    The RNG is re-seeded fresh from `seed` on every call and consumed in a
    fixed order (tef, vuln, poisson counts, primary losses, secondary trigger,
    secondary losses), so the same seed always reproduces the same draws
    regardless of the numeric values in `inputs` -- this is what lets
    apply_controls() use common random numbers (build-spec.md risk R3:
    "comparing baseline and what-if with different random draws buries small
    delta-EAL in noise").
    """
    rng = np.random.default_rng(seed)

    tef_samples = sample_pert(inputs.get("tef"), rng, n_iter)
    vuln_samples = np.clip(sample_pert(inputs.get("vuln"), rng, n_iter), 0.0, 1.0)

    lam = np.clip(tef_samples * vuln_samples, 0.0, None)
    n_events = rng.poisson(lam)
    total_events = int(n_events.sum())

    primary_losses = sample_loss_magnitude(inputs, rng, total_events, prefix="plm")
    iter_index = np.repeat(np.arange(n_iter), n_events)
    loss_vector = np.bincount(iter_index, weights=primary_losses, minlength=n_iter).astype(float)

    has_secondary_spec = any(
        k in inputs for k in ("slm_fixed", "slm_p05", "slm")
    ) and inputs.get("slef") is not None
    if has_secondary_spec and total_events > 0:
        slef_samples = np.clip(sample_pert(inputs.get("slef"), rng, n_iter), 0.0, 1.0)
        slef_per_event = np.repeat(slef_samples, n_events)
        triggered = rng.random(total_events) < slef_per_event
        n_triggered = int(triggered.sum())
        if n_triggered > 0:
            secondary_losses = sample_loss_magnitude(inputs, rng, n_triggered, prefix="slm")
            triggered_iter_index = iter_index[triggered]
            secondary_vector = np.bincount(
                triggered_iter_index, weights=secondary_losses, minlength=n_iter
            ).astype(float)
            loss_vector += secondary_vector

    tail_cap = inputs.get("tail_cap")
    if tail_cap is not None:
        loss_vector = np.minimum(loss_vector, float(tail_cap))

    return loss_vector


def summarize(loss_vector: np.ndarray, n_lec_points: int = 50) -> SummaryResult:
    """EAL = mean; VaR95/VaR99 = percentiles; LEC = 1 - empirical CDF.

    Import is local to avoid a circular import between monte_carlo and
    contracts (contracts.py re-exports SummaryResult as the public type).
    """
    from app.engine.contracts import SummaryResult

    n = len(loss_vector)
    if n == 0:
        return SummaryResult(eal=0.0, var95=0.0, var99=0.0, std_err=0.0, lec_points=[])

    eal = float(np.mean(loss_vector))
    var95 = float(np.percentile(loss_vector, 95))
    var99 = float(np.percentile(loss_vector, 99))
    std_err = float(np.std(loss_vector, ddof=1) / np.sqrt(n)) if n > 1 else 0.0

    sorted_losses = np.sort(loss_vector)[::-1]
    sample_idx = np.linspace(0, n - 1, num=min(n_lec_points, n)).astype(int)
    lec_points = [
        (float(sorted_losses[i]), float((i + 1) / n)) for i in sample_idx
    ]

    return SummaryResult(eal=eal, var95=var95, var99=var99, std_err=std_err, lec_points=lec_points)
