"""CSV importer for assets, findings and accounts, with validation
(build-spec.md section 3.1, L1). Rejected rows are logged in INGEST_RUN,
never silently dropped (CLAUDE.md: provenance on every number).

Done-when (build-spec.md section 3.1): importing an edited CSV changes
downstream figures; a malformed row is rejected and logged, not silently
dropped.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from app.data import models as m
from app.data.db import session_scope

_VALID_ASSET_ENVIRONMENTS = {"prod", "staging", "dev", "test"}
_VALID_FINDING_TYPES = {"cve", "misconfig", "iam", "coverage_gap"}
_VALID_FINDING_STATUSES = {"open", "remediated", "accepted_risk", "false_positive"}


def _new_ingest_run(session, source_name: str, kind: str) -> m.IngestRun:
    source = (
        session.query(m.DataSource).filter_by(name=source_name, kind=kind).first()
    )
    if source is None:
        source = m.DataSource(name=source_name, kind=kind, licence_note=None)
        session.add(source)
        session.flush()

    run = m.IngestRun(source_id=source.id, started_at=dt.datetime.now(dt.UTC), status="running")
    session.add(run)
    session.flush()
    return run


def _finish_ingest_run(session, run: m.IngestRun, rows_in: int, rejections: list[dict]) -> None:
    run.rows_in = rows_in
    run.rows_rejected = len(rejections)
    run.finished_at = dt.datetime.now(dt.UTC)
    run.status = "completed"
    run.rejection_log = {"rejections": rejections}


def import_assets_csv(file_path: str) -> dict:
    """Required columns: bu_id, type, hostname. Optional: internet_facing,
    environment, owner, data_sensitivity, records_held, source."""
    df = pd.read_csv(file_path, dtype=str).fillna("")

    with session_scope() as session:
        run = _new_ingest_run(session, source_name=f"csv:{file_path}", kind="csv")
        valid_bu_ids = {b.id for b in session.query(m.BusinessUnit).all()}

        rejections: list[dict] = []
        n_created = 0
        for i, row in df.iterrows():
            errors = []
            bu_id = row.get("bu_id", "")
            hostname = row.get("hostname", "")
            if not bu_id or bu_id not in valid_bu_ids:
                errors.append(f"unknown or missing bu_id: {bu_id!r}")
            if not hostname:
                errors.append("missing hostname")

            data_sensitivity_raw = row.get("data_sensitivity", "3")
            try:
                data_sensitivity = int(data_sensitivity_raw) if data_sensitivity_raw else 3
                if not (1 <= data_sensitivity <= 5):
                    errors.append(f"data_sensitivity out of range 1-5: {data_sensitivity}")
            except ValueError:
                errors.append(f"data_sensitivity not an integer: {data_sensitivity_raw!r}")
                data_sensitivity = None

            environment = row.get("environment", "prod") or "prod"
            if environment not in _VALID_ASSET_ENVIRONMENTS:
                errors.append(f"unknown environment: {environment!r}")

            if errors:
                rejections.append({"row": int(i), "errors": errors, "raw": row.to_dict()})
                continue

            records_held_raw = row.get("records_held", "0")
            records_held = int(records_held_raw) if records_held_raw else 0

            session.add(
                m.Asset(
                    bu_id=bu_id,
                    type=row.get("type", "unknown") or "unknown",
                    hostname=hostname,
                    internet_facing=str(row.get("internet_facing", "")).lower() in ("true", "1", "yes"),
                    environment=environment,
                    owner=row.get("owner") or None,
                    data_sensitivity=data_sensitivity,
                    records_held=records_held,
                    source=row.get("source", "csv_import") or "csv_import",
                )
            )
            n_created += 1

        _finish_ingest_run(session, run, rows_in=len(df), rejections=rejections)

        return {
            "ingest_run_id": run.id,
            "rows_in": len(df),
            "rows_created": n_created,
            "rows_rejected": len(rejections),
        }


def import_findings_csv(file_path: str) -> dict:
    """Required columns: asset_id, finding_type. One of cve_id/rule_id should
    be set. Optional: severity_weight, status."""
    df = pd.read_csv(file_path, dtype=str).fillna("")

    with session_scope() as session:
        run = _new_ingest_run(session, source_name=f"csv:{file_path}", kind="csv")
        valid_asset_ids = {a.id for a in session.query(m.Asset).all()}
        valid_cve_ids = {v.cve_id for v in session.query(m.Vulnerability).all()}
        valid_rule_ids = {r.rule_id for r in session.query(m.FindingRule).all()}

        rejections: list[dict] = []
        n_created = 0
        for i, row in df.iterrows():
            errors = []
            asset_id = row.get("asset_id", "")
            finding_type = row.get("finding_type", "")
            cve_id = row.get("cve_id") or None
            rule_id = row.get("rule_id") or None

            if not asset_id or asset_id not in valid_asset_ids:
                errors.append(f"unknown or missing asset_id: {asset_id!r}")
            if finding_type not in _VALID_FINDING_TYPES:
                errors.append(f"unknown finding_type: {finding_type!r}")
            if not cve_id and not rule_id:
                errors.append("finding has neither cve_id nor rule_id")
            if cve_id and cve_id not in valid_cve_ids:
                errors.append(f"unknown cve_id (not in vulnerability catalogue): {cve_id!r}")
            if rule_id and rule_id not in valid_rule_ids:
                errors.append(f"unknown rule_id: {rule_id!r}")

            status = row.get("status", "open") or "open"
            if status not in _VALID_FINDING_STATUSES:
                errors.append(f"unknown status: {status!r}")

            if errors:
                rejections.append({"row": int(i), "errors": errors, "raw": row.to_dict()})
                continue

            severity_weight_raw = row.get("severity_weight", "1.0")
            severity_weight = float(severity_weight_raw) if severity_weight_raw else 1.0

            session.add(
                m.Finding(
                    asset_id=asset_id,
                    finding_type=finding_type,
                    cve_id=cve_id,
                    rule_id=rule_id,
                    severity_weight=severity_weight,
                    status=status,
                    source_id=run.source_id,
                )
            )
            n_created += 1

        _finish_ingest_run(session, run, rows_in=len(df), rejections=rejections)

        return {
            "ingest_run_id": run.id,
            "rows_in": len(df),
            "rows_created": n_created,
            "rows_rejected": len(rejections),
        }
