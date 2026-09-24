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

# (rule_id, control_id) -- cross-framework finding-to-control mapping,
# same "starter"/confidence=0.5 pattern as csf_import.py's
# STARTER_MAPPING_RULES (build-spec.md risk R6: validate before use).
# rule_id must match a FindingRule inserted by csf_import.STARTER_FINDING_RULES;
# control_id must match a control_id in RBI_CONTROLS or SEBI_CONTROLS above.
# Only mapped where the correspondence is direct, not forced for every rule:
# - missing_mfa <-> RBI's own privileged-user MFA requirement (RBI-2026-PRIV-ACCESS)
#   is a near-exact match, not just a thematic overlap.
# - missing_logging is mapped to both regulators' 6-hour incident-reporting
#   clocks (RBI-2026-DAKSH-6H, SEBI-CSCRF-6H-EMAIL) on "intersects" (not
#   "equal") logic: without logging/monitoring coverage, an entity cannot
#   reliably detect an incident in time to meet either clock -- a real
#   control dependency, not a direct requirement match.
STARTER_CROSS_FRAMEWORK_MAPPING: list[tuple[str, str]] = [
    ("missing_mfa", "RBI-2026-PRIV-ACCESS"),
    ("missing_logging", "RBI-2026-DAKSH-6H"),
    ("missing_logging", "SEBI-CSCRF-6H-EMAIL"),
]


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

    n_mappings_created = _import_finding_mappings(session)

    return {
        "rbi_framework_id": rbi_framework.id if rbi_framework else None,
        "sebi_framework_id": sebi_framework.id if sebi_framework else None,
        "n_obligations_created": n_obligations_created,
        "n_mappings_created": n_mappings_created,
    }


def _import_finding_mappings(session) -> int:
    """Idempotent: adds STARTER_CROSS_FRAMEWORK_MAPPING rows, skipping any
    (from_id, framework_control_id) pair already present. Looked up by
    control_id across both frameworks fresh each call, so this works
    whether the RBI/SEBI controls were just created above or already
    existed from an earlier import."""
    controls_by_control_id = {
        c.control_id: c
        for c in session.query(m.FrameworkControl)
        .join(m.Framework)
        .filter(m.Framework.name.in_([RBI_FRAMEWORK_NAME, SEBI_FRAMEWORK_NAME]))
        .all()
    }
    existing_pairs = {
        (mp.from_id, mp.framework_control_id)
        for mp in session.query(m.ControlMapping).filter_by(from_kind="finding_rule").all()
    }

    n_created = 0
    for rule_id, control_id in STARTER_CROSS_FRAMEWORK_MAPPING:
        fc = controls_by_control_id.get(control_id)
        if fc is None or (rule_id, fc.id) in existing_pairs:
            continue
        session.add(
            m.ControlMapping(
                from_kind="finding_rule",
                from_id=rule_id,
                framework_control_id=fc.id,
                relationship_type="intersects",
                confidence=0.5,
                source="starter",
            )
        )
        n_created += 1
    return n_created
