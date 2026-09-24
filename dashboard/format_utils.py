"""Rupee formatting: lakh/crore convention (build-spec.md section 3.5).

"A classic off-by-one; test it" (build-spec.md risk R8) -- see
tests/test_format_utils.py for the boundary cases this must get right.
"""

from __future__ import annotations

_CRORE = 1_00_00_000  # 1,00,00,000 = 10,000,000
_LAKH = 1_00_000  # 1,00,000 = 100,000


def format_inr(amount: float) -> str:
    """Format a rupee amount using the lakh/crore convention.

    >= 1 crore  -> "₹X.XX Cr"
    >= 1 lakh   -> "₹X.XX L"
    otherwise   -> "₹X,XXX" (plain, comma-grouped)
    """
    sign = "-" if amount < 0 else ""
    magnitude = abs(amount)

    if magnitude >= _CRORE:
        return f"{sign}₹{magnitude / _CRORE:.2f} Cr"
    if magnitude >= _LAKH:
        lakh_value = magnitude / _LAKH
        if round(lakh_value, 2) >= 100.0:
            # Rounding would display "100.00 L" -- that's a full crore; don't
            # let the off-by-one land one unit short (build-spec.md risk R8).
            return f"{sign}₹{magnitude / _CRORE:.2f} Cr"
        return f"{sign}₹{lakh_value:.2f} L"
    return f"{sign}₹{magnitude:,.0f}"
