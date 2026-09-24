"""PLAN.md Task 12 / build-spec.md risk R5: ~30 test questions run through
the intent router, covering all 9 intents plus out-of-scope questions that
must get the honest fallback, not an invented answer.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.nlq.router import answer


@pytest.fixture(scope="module")
def nlq_db(tmp_path_factory, monkeypatch_module):
    import app.config as config_module
    import app.data.db as db_module
    from app.data.seed.seed import seed

    db_path = tmp_path_factory.mktemp("nlq") / "nlq.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)

    monkeypatch_module.setattr(db_module, "engine", test_engine)
    monkeypatch_module.setattr(db_module, "SessionLocal", test_session_local)
    monkeypatch_module.setattr(config_module.settings, "default_n_iter", 2_000)

    seed(reset=True)
    yield


# A pytest built-in monkeypatch fixture is function-scoped; this session
# needs a module-scoped variant so the (fairly expensive) seed() call above
# runs once for all ~30 questions rather than once per question.
@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


IN_SCOPE_QUESTIONS = [
    ("What is our highest financial cyber risk today?", "highest_risk"),
    ("What's our biggest risk right now?", "highest_risk"),
    ("Which is the riskiest part of the business?", "highest_risk"),
    ("Which vulnerabilities contribute most to our expected losses?", "top_vulnerabilities"),
    ("What are our top CVEs by risk?", "top_vulnerabilities"),
    ("List the top findings driving loss.", "top_vulnerabilities"),
    ("What is our EAL by business unit?", "eal_by_bu"),
    ("Break down expected annual loss by BU.", "eal_by_bu"),
    ("How does risk vary across business units?", "eal_by_bu"),
    ("What happens if MFA is implemented across all privileged accounts?", "whatif_mfa"),
    ("What-if we roll out MFA everywhere?", "whatif_mfa"),
    ("Show me the MFA what-if scenario.", "whatif_mfa"),
    ("How will delaying remediation by 30 days affect our financial exposure?", "delay_impact"),
    ("What's the impact of a 90 day patch delay?", "delay_impact"),
    ("If we delay remediation by 10 days, what happens?", "delay_impact"),
    ("What is the best plan for a budget of 1 crore?", "best_plan_for_budget"),
    ("Recommend an investment plan for 50 lakh.", "best_plan_for_budget"),
    ("What should we invest in with 2000000 rupees?", "best_plan_for_budget"),
    ("What are our compliance gaps?", "compliance_gaps"),
    ("Show me the framework mapping status.", "compliance_gaps"),
    ("Are there any gaps against NIST CSF?", "compliance_gaps"),
    ("What is our total expected annual loss?", "org_eal"),
    ("How much financial exposure do we have?", "org_eal"),
    ("What is our EAL?", "org_eal"),
    ("How much risk do we have overall?", "org_eal"),
    ("What are the top scenarios by risk?", "top_scenarios"),
    ("Which threat scenario is worst?", "top_scenarios"),
    ("Show me the biggest scenarios.", "top_scenarios"),
]

OUT_OF_SCOPE_QUESTIONS = [
    "What's the weather like today?",
    "Can you write me a poem about cybersecurity?",
    "What's the capital of France?",
]


@pytest.mark.parametrize("question,expected_intent", IN_SCOPE_QUESTIONS)
def test_in_scope_question_hits_expected_intent_with_real_provenance(nlq_db, question, expected_intent):
    result = answer(question)
    assert result.intent == expected_intent
    assert result.text
    if result.figures:
        assert result.provenance, "an answer with figures must carry provenance (run ID/source)"


@pytest.mark.parametrize("question", OUT_OF_SCOPE_QUESTIONS)
def test_out_of_scope_question_gets_honest_fallback(nlq_db, question):
    result = answer(question)
    assert result.intent is None
    assert "can't answer" in result.text.lower()
