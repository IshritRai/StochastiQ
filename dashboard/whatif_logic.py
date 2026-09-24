"""Plain, importable logic for the What-if page (dashboard/views/3_What_if.py).

Split out of the page module because Streamlit page files execute top-level
UI/DB code on import (st.set_page_config, session_scope() queries), so they
can't be imported directly from a test. This module has no Streamlit or DB
dependency and is safe to unit test.
"""

from __future__ import annotations

import numpy as np


def build_overrides(
    slider_values: dict[str, int], slider_defaults: dict[str, int]
) -> dict[str, float]:
    """Only send an override for a control the user actually moved.

    A slider necessarily rounds the measured coverage to the nearest integer
    percent for its default (e.g. 66.67% -> 67). If we always sent
    `new_pct / 100.0` back to apply_controls, an UNTOUCHED slider would send
    0.67 while the baseline used the exact measured 0.6667 -- a real coverage
    change apply_controls has no way to distinguish from a user's edit, so
    the "no-change" case showed a nonzero delta (docs/L1_VERIFICATION.md item
    2). Sending no override at all for untouched sliders makes apply_controls
    fall back to the exact same measured-coverage computation the baseline
    used, giving delta = 0 exactly.
    """
    return {
        ct_id: pct / 100.0
        for ct_id, pct in slider_values.items()
        if pct != slider_defaults[ct_id]
    }


def paired_stats(loss_vector: np.ndarray) -> dict[str, float]:
    any_loss = loss_vector > 0
    return {
        "p_any_loss": float(np.mean(any_loss)),
        "loss_given_event": float(np.mean(loss_vector[any_loss])) if any_loss.any() else 0.0,
        "var99": float(np.percentile(loss_vector, 99)),
    }


def paired_delta_eal_ci(
    baseline_loss_vector: np.ndarray, modified_loss_vector: np.ndarray, percentiles=(10, 90)
) -> tuple[float, float, float]:
    """Delta-EAL and its confidence interval from the PAIRED per-iteration
    difference (same seed => same iteration order => a valid paired sample),
    per docs/L1_VERIFICATION.md item 3. Returns (delta_eal, ci_low, ci_high).
    """
    delta_vector = modified_loss_vector - baseline_loss_vector
    delta_eal = float(np.mean(delta_vector))
    ci_low, ci_high = (float(x) for x in np.percentile(delta_vector, list(percentiles)))
    return delta_eal, ci_low, ci_high
