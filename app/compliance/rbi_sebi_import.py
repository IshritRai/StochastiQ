"""Imports the RBI 2026 Directions + SEBI CSCRF catalogues and reporting
obligations (PLAN.md Task 17). Mirrors csf_import.py's shape."""

from __future__ import annotations

import json

from app.compliance.rbi_sebi_data import (
    RBI_CONTROLS,
    RBI_EFFECTIVE_DATE,
    RBI_FRAMEWORK_NAME,
    RBI_SOURCE_URL,
    RBI_VERSION,
    REPORTING_OBLIGATIONS,
    SEBI_CONTROLS,
    SEBI_EFFECTIVE_DATE,
    SEBI_FRAMEWORK_NAME,
    SEBI_SOURCE_URL,
    SEBI_VERSION,
)
from app.data import models as m


def _import_framework(session, name, version, effective_date, source_url, controls):
    framework = m.Framework(
        name=name,
        version=version,
        effective_date=effective_date,
        licence_tier="public",
        source_url=source_url,
        retired=False,
    )
    session.add(framework)
    session.flush()

    for control_id, short_title, source_ref, verified in controls:
        session.add(
            m.FrameworkControl(
                framework_id=framework.id,
                control_id=control_id,
                short_title=short_title,
                parent_id=None,
                status="active",
                source_ref=source_ref,
                verified=verified,
            )
        )
    session.flush()
    return framework


def import_rbi_sebi_catalogue(session) -> dict:
    """Idempotent: skips import if these frameworks already exist (matches
    csf_import's single-import-per-DB pattern used by app.data.seed.seed)."""
    existing_names = {f.name for f in session.query(m.Framework).all()}

    rbi_framework = None
    if RBI_FRAMEWORK_NAME not in existing_names:
        rbi_framework = _import_framework(
            session, RBI_FRAMEWORK_NAME, RBI_VERSION, RBI_EFFECTIVE_DATE, RBI_SOURCE_URL, RBI_CONTROLS
        )

    sebi_framework = None
    if SEBI_FRAMEWORK_NAME not in existing_names:
        sebi_framework = _import_framework(
            session, SEBI_FRAMEWORK_NAME, SEBI_VERSION, SEBI_EFFECTIVE_DATE, SEBI_SOURCE_URL, SEBI_CONTROLS
        )

    existing_regimes = {o.regime for o in session.query(m.ReportingObligation).all()}
    n_obligations_created = 0
    for regime, clock_hours, recipient, trigger, entity_types, effective_from, source_ref, verified in REPORTING_OBLIGATIONS:
        if regime in existing_regimes:
            continue
        session.add(
            m.ReportingObligation(
                regime=regime,
                entity_types=json.dumps(entity_types),
                clock_hours=clock_hours,
                recipient=recipient,
                trigger=trigger,
                effective_from=effective_from,
                source_ref=source_ref,
                verified=verified,
            )
        )
        n_obligations_created += 1

    return {
        "rbi_framework_id": rbi_framework.id if rbi_framework else None,
        "sebi_framework_id": sebi_framework.id if sebi_framework else None,
        "n_obligations_created": n_obligations_created,
    }
