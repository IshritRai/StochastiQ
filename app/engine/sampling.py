"""Distribution sampling helpers for the Monte Carlo engine.

Beta-PERT for bounded inputs (frequencies, probabilities), lognormal fitted
to a 5th/95th percentile pair for loss magnitudes -- both the de facto
choices identified in docs/research/fair-based-cyber-risk.md ("PERT ... is
the de facto default in practice"; "riskquant maps a [low, high] 90% range
to a lognormal so that they fall at the 5% and 95% cumulative probability
points").
"""

from __future__ import annotations

import numpy as np

# z-score for the 5th/95th percentile pair of a standard normal (90% CI).
_Z_90 = 1.6448536269514722


def sample_pert(spec: float | dict | None, rng: np.random.Generator, n: int) -> np.ndarray:
    """Sample n draws of a factor given as either a scalar or a {low, mode, high} dict.

    A scalar is returned as a constant array (useful for guardrail tests that
    fix a factor exactly). A dict samples a Beta-PERT distribution.
    """
    if spec is None:
        return np.zeros(n)
    if isinstance(spec, (int, float)):
        return np.full(n, float(spec))

    low, mode, high = float(spec["low"]), float(spec["mode"]), float(spec["high"])
    if high <= low:
        return np.full(n, mode)

    alpha = 1.0 + 4.0 * (mode - low) / (high - low)
    beta = 1.0 + 4.0 * (high - mode) / (high - low)
    return low + rng.beta(alpha, beta, size=n) * (high - low)


def fit_lognormal_params(p05: float, p95: float) -> tuple[float, float]:
    """Fit a lognormal's (mu, sigma) so its 5th/95th percentiles match p05/p95."""
    if p05 <= 0 or p95 <= 0 or p95 <= p05:
        raise ValueError("fit_lognormal_params requires 0 < p05 < p95")
    log_p05, log_p95 = np.log(p05), np.log(p95)
    sigma = (log_p95 - log_p05) / (2.0 * _Z_90)
    mu = (log_p95 + log_p05) / 2.0
    return mu, sigma


def sample_loss_magnitude(
    spec: dict, rng: np.random.Generator, n: int, prefix: str
) -> np.ndarray:
    """Sample n loss-magnitude draws for a factor family (e.g. "plm" or "slm").

    Supports three input shapes, checked in order:
      - ``{prefix}_fixed``: a deterministic amount (used by guardrail tests).
      - ``{prefix}_p05`` / ``{prefix}_p95``: lognormal fit to a 90% CI.
      - ``{prefix}``: a {low, mode, high} dict, treated as a PERT range
        (used when a scenario's rationale only supports a rough range).
    """
    if n == 0:
        return np.array([])

    fixed_key = f"{prefix}_fixed"
    if fixed_key in spec:
        return np.full(n, float(spec[fixed_key]))

    p05_key, p95_key = f"{prefix}_p05", f"{prefix}_p95"
    if p05_key in spec and p95_key in spec:
        mu, sigma = fit_lognormal_params(float(spec[p05_key]), float(spec[p95_key]))
        return rng.lognormal(mean=mu, sigma=sigma, size=n)

    if prefix in spec and isinstance(spec[prefix], dict):
        return sample_pert(spec[prefix], rng, n)

    raise KeyError(
        f"No loss spec found for prefix '{prefix}': expected one of "
        f"'{fixed_key}', ('{p05_key}', '{p95_key}'), or '{prefix}'"
    )
