"""PLAN.md Task 1 done-when test: `make seed` twice gives identical data.

Primary keys are random UUIDs (not seed-derived), so "identical" is checked
on content: same row counts per table and the same numeric aggregates,
rather than byte-identical primary keys. That is the practically meaningful
form of reproducibility for a demo (build-spec.md 3.1's acceptance test is
about downstream figures being stable, not about literal UUID equality).
"""

from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.data import models as m
from app.data.seed.seed import seed


def _seed_fresh_db(db_path: str) -> dict:
    import app.config as config_module
    import app.data.db as db_module

    config_module.settings.database_url = f"sqlite:///{db_path}"
    db_module.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    db_module.SessionLocal = sessionmaker(bind=db_module.engine, autoflush=False, autocommit=False)

    seed(reset=True)

    session = db_module.SessionLocal()
    try:
        snapshot = {
            "n_business_units": session.scalar(select(func.count()).select_from(m.BusinessUnit)),
            "n_assets": session.scalar(select(func.count()).select_from(m.Asset)),
            "n_services": session.scalar(select(func.count()).select_from(m.BusinessService)),
            "n_scenarios": session.scalar(select(func.count()).select_from(m.ThreatScenario)),
            "n_scenario_inputs": session.scalar(select(func.count()).select_from(m.ScenarioInput)),
            "n_control_types": session.scalar(select(func.count()).select_from(m.ControlType)),
            "total_records_held": session.scalar(select(func.sum(m.Asset.records_held))),
            "total_criticality": session.scalar(select(func.sum(m.Asset.criticality))),
            "sum_coverage_pct": session.scalar(select(func.sum(m.ControlState.coverage_pct))),
        }
    finally:
        session.close()
    return snapshot


def test_seed_is_reproducible_across_two_runs():
    with tempfile.TemporaryDirectory() as tmp:
        db_a = os.path.join(tmp, "a.db")
        db_b = os.path.join(tmp, "b.db")
        snap_a = _seed_fresh_db(db_a)
        snap_b = _seed_fresh_db(db_b)
        assert snap_a == snap_b


def test_seed_produces_the_spec_shape():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "shape.db")
        snap = _seed_fresh_db(db_path)
        assert snap["n_business_units"] == 3
        assert snap["n_services"] == 3
        assert snap["n_scenarios"] == 8
        assert snap["n_assets"] >= 27  # ~30 assets target, per PLAN.md Task 1
