"""answer(question) -> Answer(text, figures, provenance), per build-spec.md
section 2.2. L1: a keyword/regex intent router over a fixed set of real
functions (build-spec.md section 3.3) -- no LLM yet (that's Task 16's
Gemini tool-calling upgrade). Code inserts every number; there is nothing
for a model to phrase or invent at L1 (build-spec.md risk R5)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Answer:
    text: str
    figures: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    intent: str | None = None  # None means "no intent matched" (honest fallback)
