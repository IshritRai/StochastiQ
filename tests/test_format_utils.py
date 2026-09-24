"""build-spec.md risk R8: lakh/crore formatting is a classic off-by-one; test it."""

from __future__ import annotations

import pytest

from dashboard.format_utils import format_inr


@pytest.mark.parametrize(
    "amount,expected",
    [
        (0, "₹0"),
        (999, "₹999"),
        (99_999, "₹99,999"),
        (100_000, "₹1.00 L"),  # exact lakh boundary
        (100_001, "₹1.00 L"),
        (250_000, "₹2.50 L"),
        (9_999_999, "₹1.00 Cr"),  # just under 1 crore, but rounds up to it -- must not show "100.00 L"
        (10_000_000, "₹1.00 Cr"),  # exact crore boundary
        (10_000_001, "₹1.00 Cr"),
        (123_456_789, "₹12.35 Cr"),
        (-250_000, "-₹2.50 L"),
    ],
)
def test_format_inr_boundaries(amount, expected):
    assert format_inr(amount) == expected
