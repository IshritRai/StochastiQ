"""FastAPI app. The engine (app/engine) is a plain library, imported here and
by the Streamlit dashboard directly -- no microservices (CLAUDE.md).

Routers for scenarios/runs/attribution/optimize/compliance/nlq are added as
their backing engine functions land (PLAN.md Tasks 3-4, 6, 11-12).
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="StochastiQ", description="Cyber risk quantification engine API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
