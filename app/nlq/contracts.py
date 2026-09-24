"""answer(question) -> Answer(text, figures, provenance).
L1: a keyword/regex intent router over a fixed set of real functions,
no LLM yet (that's the Gemini tool-calling upgrade). Code inserts every
number; there is nothing for a model to phrase or invent at L1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Answer:
    text: str
    figures: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    intent: str | None = None  # None means "no intent matched" (honest fallback)
