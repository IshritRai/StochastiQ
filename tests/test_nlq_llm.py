"""Task 16 / build-spec.md risk R5: the Gemini phrasing layer must never
introduce a number that isn't already in the structured tool-call result
(Answer.figures). Written before app/nlq/llm_router.py exists, per
CLAUDE.md's "tests before dependents build on a function".

Also covers the required graceful-degradation behavior: no/invalid
GEMINI_API_KEY must fall back to Task 12's rule-based router with the 9
existing intents unaffected.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.nlq.contracts import Answer


@pytest.fixture(scope="module")
def nlq_db(tmp_path_factory, monkeypatch_module):
    import app.config as config_module
    import app.data.db as db_module
    from app.data.seed.seed import seed

    db_path = tmp_path_factory.mktemp("nlq_llm") / "nlq.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)

    monkeypatch_module.setattr(db_module, "engine", test_engine)
    monkeypatch_module.setattr(db_module, "SessionLocal", test_session_local)
    monkeypatch_module.setattr(config_module.settings, "default_n_iter", 2_000)

    seed(reset=True)
    yield


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


# ---------------------------------------------------------------------------
# R5 guardrail: number-grounding check, no DB or network needed.
# ---------------------------------------------------------------------------


def test_grounded_text_passes():
    from app.nlq.llm_router import verify_numbers_grounded

    figures = {"eal": 12345678.9, "var95": 987654.0}
    text = "Expected Annual Loss is Rs 12,345,679 (VaR95: Rs 987,654)."
    assert verify_numbers_grounded(text, figures)


def test_invented_number_fails():
    from app.nlq.llm_router import verify_numbers_grounded

    figures = {"eal": 12345678.9}
    text = "Expected Annual Loss is roughly Rs 99,000,000, a 40% increase."
    assert not verify_numbers_grounded(text, figures)


def test_empty_figures_with_no_numbers_passes():
    from app.nlq.llm_router import verify_numbers_grounded

    assert verify_numbers_grounded("No numeric claim here.", {})


# ---------------------------------------------------------------------------
# End-to-end: allow-listed tool-calling with a fake Gemini client. Gemini is
# mocked here (never hits the network in tests); the real live call is
# smoke-tested manually via the dashboard, not in CI.
# ---------------------------------------------------------------------------


def test_llm_answer_uses_only_structured_result_numbers(nlq_db, monkeypatch):
    from app.nlq import gemini_client, llm_router

    monkeypatch.setattr(gemini_client, "select_intent", lambda question, allowed: "org_eal")

    captured_figures = {}

    def fake_phrase_answer(question, intent, figures, fallback_text):
        captured_figures.update(figures)
        # Deliberately invents a number that is NOT in figures.
        return "Our exposure is a made-up Rs 999,999,999,999 this year."

    monkeypatch.setattr(gemini_client, "phrase_answer", fake_phrase_answer)

    result = llm_router.try_answer("What is our EAL?")

    assert isinstance(result, Answer)
    assert captured_figures  # phrase_answer was actually given the real figures
    # The fabricated number must have been rejected: result text must be the
    # code-generated fallback, not Gemini's invented figure.
    assert "999,999,999,999" not in result.text
    for value in captured_figures.values():
        assert isinstance(value, (int, float))


def test_llm_answer_passes_through_when_grounded(nlq_db, monkeypatch):
    from app.nlq import gemini_client, llm_router

    monkeypatch.setattr(gemini_client, "select_intent", lambda question, allowed: "org_eal")

    def fake_phrase_answer(question, intent, figures, fallback_text):
        eal = figures["eal"]
        return f"Your organization's yearly expected loss is about {eal:.0f}."

    monkeypatch.setattr(gemini_client, "phrase_answer", fake_phrase_answer)

    result = llm_router.try_answer("What is our EAL?")
    assert "yearly expected loss" in result.text


def test_llm_unavailable_falls_back_to_none(monkeypatch):
    """No/invalid GEMINI_API_KEY (select_intent returns None) means the LLM
    layer must step out of the way entirely so the rule-based router runs."""
    from app.nlq import gemini_client, llm_router

    monkeypatch.setattr(gemini_client, "select_intent", lambda question, allowed: None)
    assert llm_router.try_answer("What is our EAL?") is None


def test_answer_still_works_without_gemini_key(nlq_db, monkeypatch):
    """The 9 existing intents must keep working with no key at all."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app.nlq import gemini_client

    gemini_client._client = None
    gemini_client._unavailable = False

    from app.nlq.router import answer

    result = answer("What is our EAL?")
    assert result.intent == "org_eal"
    assert result.text
