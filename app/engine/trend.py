"""EAL trend over stored SimulationRun rows.

The "no seed-per-refresh noise" guardrail means the trend must not mix
runs from different seeds: a run-to-run EAL change should reflect a real
change in the DB (a new finding, a control coverage change, a fresh
`make fetch-vuln-intel`), never Monte Carlo noise from re-rolling the seed.
`org_eal_trend` therefore filters to a single seed (the caller's, default
`settings.default_seed`) and org-level runs (`scenario_id IS NULL`) only.
"""

from __future__ import annotations

from app.config import settings
from app.data import models as m
from app.data.db import session_scope


def org_eal_trend(seed: int | None = None, limit: int = 50) -> list[dict]:
    seed = seed if seed is not None else settings.default_seed
    with session_scope() as session:
        runs = (
            session.query(m.SimulationRun)
            .filter(m.SimulationRun.scenario_id.is_(None), m.SimulationRun.seed == seed)
            .order_by(m.SimulationRun.snapshot_at)
            .limit(limit)
            .all()
        )
        return [
            {
                "run_id": r.id,
                "snapshot_at": r.snapshot_at,
                "eal": r.eal,
                "var95": r.var95,
                "inputs_hash": r.inputs_hash,
            }
            for r in runs
        ]
