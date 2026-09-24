"""Shared fixtures: an isolated, file-backed SQLite DB per test for engine tests.

Isolated per test (not the full synthetic seed from app.data.seed.seed) so
guardrail tests can set up exactly the minimal scenarios build-spec.md's R3
tests need, independent of how the demo company generator evolves.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.data import models as m


@pytest.fixture()
def engine_db(monkeypatch, tmp_path):
    import app.data.db as db_module

    db_path = tmp_path / "engine_test.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    test_session_local = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", test_session_local)

    m.Base.metadata.create_all(bind=test_engine)

    yield test_session_local

    m.Base.metadata.drop_all(bind=test_engine)


def make_scenario(
    session,
    scenario_id: str,
    *,
    tef=(0.5, 1.0, 2.0),
    vuln=(0.2, 0.4, 0.6),
    plm_p05=1_000.0,
    plm_p95=100_000.0,
    slef=(0.0, 0.0, 0.0),
    slm_p05=None,
    slm_p95=None,
):
    """Insert one ThreatScenario plus its ScenarioInput rows for engine tests."""
    scenario = m.ThreatScenario(
        id=scenario_id,
        name=scenario_id,
        threat_community="test",
        scope_rule="{}",
        description="test fixture scenario",
        active=True,
    )
    session.add(scenario)

    def _add(factor, low, mode, high):
        session.add(
            m.ScenarioInput(
                scenario_id=scenario_id,
                factor=factor,
                low=low,
                mode=mode,
                high=high,
                distribution="pert",
                confidence=0.90,
                calibration_source="test fixture",
                population="test",
                rationale="test fixture value",
            )
        )

    _add("TEF", *tef)
    _add("Vuln", *vuln)
    _add("PLM", plm_p05, (plm_p05 + plm_p95) / 2, plm_p95)
    _add("SLEF", *slef)
    if slm_p05 is not None and slm_p95 is not None:
        _add("SLM", slm_p05, (slm_p05 + slm_p95) / 2, slm_p95)

    session.flush()
    return scenario
