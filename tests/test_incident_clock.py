"""PLAN.md Task 17: RBI/SEBI/CERT-In/DPDP catalogues and the incident-clock
engine. Done-when: "feeding one detection timestamp produces all clocks
correctly, including DPDP showing 'not yet in force' before 13 May 2027."
"""

from __future__ import annotations

import datetime as dt

from app.compliance.incident_clock import compute_incident_clocks
from app.compliance.rbi_sebi_import import import_rbi_sebi_catalogue
from app.data import models as m


def test_catalogue_import_creates_frameworks_and_obligations(engine_db):
    session = engine_db()
    result = import_rbi_sebi_catalogue(session)
    session.commit()

    assert result["rbi_framework_id"] is not None
    assert result["sebi_framework_id"] is not None
    assert result["n_obligations_created"] == 9

    session = engine_db()
    frameworks = {f.name for f in session.query(m.Framework).all()}
    assert any("Non-Banking Financial Companies" in name for name in frameworks)
    assert "SEBI Cybersecurity and Cyber Resilience Framework (CSCRF)" in frameworks

    # FrameworkControl rows: RBI's paragraphs were confirmed against the
    # primary RBI/DoS/2026-27/461 PDF (read in full in this session), and
    # SEBI's against its primary CSCRF circular plus its own CSCRF FAQ PDF
    # (Annexure-O forensic-report requirement, Q76). Only SEBI-CSCRF-VAPT
    # remains unverified: the FAQ's "3 months" VAPT-closure figure is for a
    # different (periodic cyber-audit) VAPT cycle, not confirmed as this
    # same incident-response item (see rbi_sebi_data.py's module docstring).
    controls = {c.control_id: c for c in session.query(m.FrameworkControl).all()}
    assert controls
    unverified_controls = {"SEBI-CSCRF-VAPT"}
    for control_id, control in controls.items():
        expected = control_id not in unverified_controls
        assert control.verified is expected, control_id

    # ReportingObligation rows: the SEBI CSCRF timelines, RBI's DAKSH
    # paragraph, the standing CERT-In direction, and now DPDP's 72-hour
    # clock (confirmed against the actual Gazette text, G.S.R. 846(E)) are
    # all verified against primary sources.
    obligations = {o.regime: o for o in session.query(m.ReportingObligation).all()}
    unverified_regimes: set[str] = set()
    for regime, obligation in obligations.items():
        expected = regime not in unverified_regimes
        assert obligation.verified is expected, regime


def test_import_is_idempotent(engine_db):
    session = engine_db()
    import_rbi_sebi_catalogue(session)
    session.commit()
    session.close()

    session = engine_db()
    result = import_rbi_sebi_catalogue(session)
    session.commit()
    assert result["rbi_framework_id"] is None  # already existed, not re-created
    assert result["n_obligations_created"] == 0


def test_one_detection_timestamp_produces_all_clocks_before_dpdp_commencement(engine_db):
    session = engine_db()
    import_rbi_sebi_catalogue(session)
    session.commit()
    session.close()

    session = engine_db()
    detected_at = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.UTC)
    clocks = compute_incident_clocks(session, detected_at)

    by_regime = {c.regime: c for c in clocks}
    assert set(by_regime) == {
        "rbi_daksh",
        "cert_in",
        "sebi_email",
        "sebi_portal",
        "sebi_interim",
        "sebi_mitigation",
        "sebi_rca",
        "sebi_closure",
        "dpdp_breach",
    }

    assert by_regime["rbi_daksh"].deadline == detected_at + dt.timedelta(hours=6)
    assert by_regime["rbi_daksh"].in_force is True
    assert by_regime["cert_in"].deadline == detected_at + dt.timedelta(hours=6)
    assert by_regime["sebi_email"].deadline == detected_at + dt.timedelta(hours=6)
    assert by_regime["sebi_portal"].deadline == detected_at + dt.timedelta(hours=24)
    assert by_regime["sebi_interim"].deadline == detected_at + dt.timedelta(days=3)
    assert by_regime["sebi_mitigation"].deadline == detected_at + dt.timedelta(days=7)
    assert by_regime["sebi_rca"].deadline == detected_at + dt.timedelta(days=30)
    assert by_regime["sebi_closure"].deadline == detected_at + dt.timedelta(days=75)

    # DPDP: detection is well before the 13 May 2027 commencement date.
    dpdp = by_regime["dpdp_breach"]
    assert dpdp.in_force is False
    assert dpdp.deadline is None
    assert "not yet in force" in dpdp.note.lower()
    assert "2027-05-13" in dpdp.note


def test_dpdp_clock_applies_after_commencement_date(engine_db):
    session = engine_db()
    import_rbi_sebi_catalogue(session)
    session.commit()
    session.close()

    session = engine_db()
    detected_at = dt.datetime(2027, 6, 1, tzinfo=dt.UTC)  # after 13 May 2027
    clocks = compute_incident_clocks(session, detected_at)
    dpdp = next(c for c in clocks if c.regime == "dpdp_breach")

    assert dpdp.in_force is True
    assert dpdp.deadline == detected_at + dt.timedelta(hours=72)


def test_entity_type_filter_excludes_inapplicable_regimes(engine_db):
    session = engine_db()
    import_rbi_sebi_catalogue(session)
    session.commit()
    session.close()

    session = engine_db()
    detected_at = dt.datetime(2026, 10, 1, tzinfo=dt.UTC)
    clocks = compute_incident_clocks(session, detected_at, entity_type="bank")
    regimes = {c.regime for c in clocks}
    assert "rbi_daksh" in regimes
    assert "sebi_email" not in regimes  # SEBI regimes apply to market entities, not banks
