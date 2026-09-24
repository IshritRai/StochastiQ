"""Thin wrapper around the Gemini API (google-genai SDK), used only for two
narrow jobs in the NL layer:

1. select_intent: pick ONE name from a fixed allow-list of existing,
   already-tested intent handlers (app/nlq/router.py's 9 _handle_* functions).
   Gemini never gets to run arbitrary code, query the DB directly, or invent
   an intent that isn't in the allow-list.
2. phrase_answer: turn an already-computed structured result (figures the
   *code* computed, not the model) into one natural sentence. Gemini is
   explicitly instructed to use only the given numbers; app/nlq/llm_router.py
   independently verifies that afterwards (it does not trust the instruction
   alone).

Any failure here -- missing/invalid GEMINI_API_KEY, no network, a rate limit,
a malformed response -- is caught and turned into `None`. Callers treat
`None` as "the LLM layer is unavailable" and fall back to Task 12's
rule-based router, so the 9 existing intents keep working with no Gemini key
at all.
"""

from __future__ import annotations

import json
import os

_MODEL = "gemini-3.6-flash"

# Cached client + a "don't retry" flag so a missing/invalid key or a broken
# import doesn't re-attempt client construction on every single question.
_client = None
_unavailable = False


def _get_client():
    global _client, _unavailable
    if _unavailable:
        return None
    if _client is not None:
        return _client

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        _unavailable = True
        return None

    try:
        from google import genai

        _client = genai.Client(api_key=api_key)
    except Exception:
        _unavailable = True
        return None
    return _client


def select_intent(question: str, allowed_intents: list[str]) -> str | None:
    """Ask Gemini to classify `question` into exactly one of
    `allowed_intents`. Returns None on any failure or when the response
    isn't one of the allowed names (a fixed allow-list, never freeform)."""
    client = _get_client()
    if client is None:
        return None

    prompt = (
        "You are a strict classifier for a cyber-risk NL query system. "
        "Choose exactly one intent name from this fixed list that best "
        f"matches the user's question: {allowed_intents}. "
        "Respond with ONLY the intent name and nothing else -- no "
        "punctuation, no explanation. If none of them fit, respond with "
        "the single word: none\n\n"
        f"Question: {question!r}"
    )
    try:
        resp = client.models.generate_content(model=_MODEL, contents=prompt)
        name = (resp.text or "").strip().strip('"').strip("'").strip()
    except Exception:
        return None
    return name if name in allowed_intents else None


def phrase_answer(question: str, intent: str, figures: dict, fallback_text: str) -> str | None:
    """Ask Gemini to phrase one sentence for `question`, using only the
    numbers already present in `figures` (computed by code: EPSS/VaR/etc.
    must never be phrased as something the model derived). Returns None on
    any failure; the caller also independently re-checks the numbers, so
    this is defense in depth, not the only guardrail."""
    client = _get_client()
    if client is None:
        return None

    prompt = (
        "You are a cyber-risk reporting assistant writing for a risk "
        "manager. Rewrite the machine-computed answer below into ONE "
        "natural, concise sentence.\n\n"
        "Hard rules:\n"
        "- Use ONLY the numbers listed in FIGURES. Do not compute, round "
        "differently, convert units, or invent ANY number not present "
        "there.\n"
        "- Do not add percentages, comparisons, or figures that are not "
        "in FIGURES.\n"
        "- If you are unsure a number is correct, omit it rather than "
        "guess.\n\n"
        f"QUESTION: {question}\n"
        f"FIGURES (JSON -- the only numbers you may use): {json.dumps(figures, default=str)}\n"
        f"MACHINE-GENERATED BASELINE ANSWER (already numerically correct): {fallback_text}\n\n"
        "Your rewritten sentence:"
    )
    try:
        resp = client.models.generate_content(model=_MODEL, contents=prompt)
        text = (resp.text or "").strip()
    except Exception:
        return None
    return text or None
