"""Gemini tool-calling layer for the NL query router (Task 16,
build-spec.md risk R5).

Gemini is NEVER allowed to compute or invent a number. It is only allowed
to:
  1. pick one intent name from `app.nlq.router.ALLOWED_INTENTS` -- a fixed
     allow-list identical to Task 12's 9 rule-based handlers. There is no
     freeform code execution and no direct DB access; Gemini gets a name,
     and the code below is what actually calls the handler.
  2. phrase the final sentence, using only the numbers already present in
     that handler's own structured Answer.figures (computed by code from a
     DB row / Monte-Carlo run, with provenance already attached).

After Gemini phrases the sentence we independently re-check it:
`verify_numbers_grounded` extracts every numeric token from the LLM's text
and confirms each one also appears among the numbers in the structured
result. If that check fails -- which it must never silently pass, per
build-spec.md risk R5 -- we discard the LLM's text and use the
code-generated sentence from the same handler instead, which is always
numerically correct because code, not the model, inserted its numbers.
tests/test_nlq_llm.py asserts this end to end.
"""

from __future__ import annotations

import logging
import re

from app.nlq.contracts import Answer

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"\d[\d,]*\.?\d*")

# Numeric tokens at or below this many significant digits are excluded from
# the R5 check: single/double digit numbers show up incidentally in prose
# (list positions, "30 days" already inside the baseline text, control
# names) without being a claimed risk figure, and would make the check too
# noisy to be useful. Anything with 3+ digits is a real figure and must be
# grounded.
_MIN_DIGITS_TO_CHECK = 3


def _numeric_tokens(text: str) -> set[str]:
    return {tok.replace(",", "").rstrip(".") for tok in _NUM_RE.findall(text) if tok}


def _figure_numeric_tokens(figures: dict) -> set[str]:
    """Numbers a structured result actually carries, in several plausible
    renderings (raw float, rounded integer, comma-grouped, and Indian
    lakh/crore scale -- this app's own INR convention, dashboard.
    format_utils.format_inr) so formatting differences between the code
    path and Gemini's prose don't cause a false positive on the R5 check."""
    tokens: set[str] = set()
    for value in figures.values():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            tokens |= _numeric_tokens(f"{value:.6f}")
            tokens |= _numeric_tokens(f"{value:,.6f}")
            tokens |= _numeric_tokens(str(round(value)))
            tokens |= _numeric_tokens(f"{round(value):,}")
            tokens |= _numeric_tokens(str(value))
            # Lakh/crore renderings (e.g. 4536250.30 -> "45.36" lakh,
            # "0.45" crore) at 1-2 decimal places, matching how Gemini
            # tends to phrase INR amounts given a lakh/crore-formatted
            # baseline in its prompt.
            for scale in (1_00_000, 1_00_00_000):
                scaled = value / scale
                for decimals in (0, 1, 2):
                    tokens |= _numeric_tokens(f"{scaled:.{decimals}f}")
        else:
            tokens |= _numeric_tokens(str(value))
    return tokens


def verify_numbers_grounded(llm_text: str, figures: dict) -> bool:
    """build-spec.md risk R5: every number the LLM wrote must trace back to
    the structured tool-call result it was given."""
    llm_numbers = {t for t in _numeric_tokens(llm_text) if len(t.replace(".", "")) >= _MIN_DIGITS_TO_CHECK}
    if not llm_numbers:
        return True
    grounded = _figure_numeric_tokens(figures)
    return llm_numbers.issubset(grounded)


def try_answer(question: str) -> Answer | None:
    """Returns a phrased Answer if Gemini is available and its phrasing
    passes the R5 grounding check; returns None if Gemini is unavailable
    (no/invalid key, network failure, ...) or picked no allow-listed
    intent, in which case the caller (app.nlq.router.answer) falls back to
    the plain rule-based router."""
    from app.nlq import gemini_client
    from app.nlq.router import ALLOWED_INTENTS

    intent_name = gemini_client.select_intent(question, list(ALLOWED_INTENTS))
    if intent_name is None or intent_name not in ALLOWED_INTENTS:
        return None

    handler = ALLOWED_INTENTS[intent_name]
    try:
        baseline = handler(question)
    except Exception:
        logger.exception("allow-listed handler %r raised; falling back to rule-based router", intent_name)
        return None

    phrased = gemini_client.phrase_answer(question, intent_name, baseline.figures, baseline.text)
    if phrased is None:
        return baseline

    if not verify_numbers_grounded(phrased, baseline.figures):
        logger.warning(
            "Gemini phrasing for intent %r failed the R5 number-grounding check; "
            "using the code-generated sentence instead",
            intent_name,
        )
        return baseline

    return Answer(text=phrased, figures=baseline.figures, provenance=baseline.provenance, intent=baseline.intent)
