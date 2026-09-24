"""Incident-clock engine: turns one detection timestamp into every
applicable regulatory reporting deadline, reading ReportingObligation
rows from the DB (never hard-coded here) so `make enrich-vuln-intel`-style
catalogue updates change the clocks without a code change.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass

from app.data import models as m


@dataclass
class IncidentClock:
    regime: str
    recipient: str
    clock_hours: float
    deadline: dt.datetime | None
    in_force: bool
    note: str | None
    source_ref: str | None
    verified: bool


def compute_incident_clocks(
    session, detected_at: dt.datetime, entity_type: str | None = None
) -> list[IncidentClock]:
    """Returns one IncidentClock per ReportingObligation row (optionally
    filtered to those applicable to `entity_type`), each with its deadline
    computed from `detected_at`, except a regime whose
    `effective_from` is still in the future relative to `detected_at`,
    which is returned with `in_force=False` and `deadline=None`
    (e.g. DPDP showing "not yet in force" before 13 May 2027)."""
    if detected_at.tzinfo is None:
        detected_at = detected_at.replace(tzinfo=dt.UTC)

    obligations = session.query(m.ReportingObligation).order_by(m.ReportingObligation.clock_hours).all()
    clocks: list[IncidentClock] = []

    for obligation in obligations:
        if entity_type is not None:
            entity_types = json.loads(obligation.entity_types)
            if entity_type not in entity_types:
                continue

        effective_from = obligation.effective_from
        if effective_from is not None and effective_from.tzinfo is None:
            effective_from = effective_from.replace(tzinfo=dt.UTC)

        if effective_from is not None and detected_at < effective_from:
            clocks.append(
                IncidentClock(
                    regime=obligation.regime,
                    recipient=obligation.recipient,
                    clock_hours=obligation.clock_hours,
                    deadline=None,
                    in_force=False,
                    note=f"Not yet in force (effective from {effective_from.date().isoformat()})",
                    source_ref=obligation.source_ref,
                    verified=obligation.verified,
                )
            )
            continue

        deadline = detected_at + dt.timedelta(hours=obligation.clock_hours)
        clocks.append(
            IncidentClock(
                regime=obligation.regime,
                recipient=obligation.recipient,
                clock_hours=obligation.clock_hours,
                deadline=deadline,
                in_force=True,
                note=None,
                source_ref=obligation.source_ref,
                verified=obligation.verified,
            )
        )

    return clocks
