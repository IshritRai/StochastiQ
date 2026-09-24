"""Imports the NIST CSF 2.0 structure (app/compliance/csf_data.py) and a
starter finding-to-control mapping (build-spec.md section 3.6, L1).

The starter mapping below reuses the exact (finding-type, CSF-subcategory)
pairs from docs/research/control_mapping.md section 1e's worked table,
which already carries its own source trail back to NIST's Informative
References / OLIR. Every row is inserted with source="starter" and
confidence=0.5, per that table's own instruction: "Validate every row with
an assessor before use" (build-spec.md risk R6: "mappings labelled starter
until validated").
"""

from __future__ import annotations

from app.compliance.csf_data import (
    CSF_CATEGORIES,
    CSF_EFFECTIVE_DATE,
    CSF_SOURCE_URL,
    CSF_SUBCATEGORIES,
    CSF_VERSION,
    WITHDRAWN_CSF_1_1_IDS,
)
from app.data import models as m

FRAMEWORK_NAME = "NIST CSF"

# (rule_id, title, category, default_severity_weight)
STARTER_FINDING_RULES: list[tuple[str, str, str, float]] = [
    ("missing_mfa", "MFA missing on privileged account", "iam", 3.0),
    ("open_ports", "Unnecessary open port exposed", "misconfig", 2.0),
    ("weak_tls", "Weak TLS/certificate configuration", "misconfig", 1.5),
    ("exposed_storage", "Publicly exposed data store", "misconfig", 4.0),
    ("missing_logging", "Missing centralized logging/monitoring", "coverage_gap", 2.0),
    ("no_asset_inventory", "Asset missing from inventory", "coverage_gap", 1.0),
]

# (from_kind, from_id, subcategory_id) -- from_id for "control_type" is
# resolved by NAME at import time (control_type_id is a generated UUID, not
# known until the control types are seeded).
STARTER_MAPPING_RULES: list[tuple[str, str]] = [
    ("missing_mfa", "PR.AA-03"),
    ("missing_mfa", "PR.AA-01"),
    ("open_ports", "PR.IR-01"),
    ("open_ports", "ID.AM-03"),
    ("weak_tls", "PR.DS-02"),
    ("exposed_storage", "PR.DS-01"),
    ("exposed_storage", "PR.AA-05"),
    ("exposed_storage", "PR.PS-01"),
    ("missing_logging", "PR.PS-04"),
    ("missing_logging", "DE.CM-01"),
    ("missing_logging", "DE.CM-03"),
    ("missing_logging", "DE.CM-09"),
    ("missing_logging", "DE.AE-03"),
    ("no_asset_inventory", "ID.AM-01"),
    ("no_asset_inventory", "ID.AM-02"),
]

STARTER_MAPPING_CONTROL_TYPES: list[tuple[str, str]] = [
    ("Patch / vulnerability management", "ID.RA-01"),
    ("Patch / vulnerability management", "PR.PS-02"),
    ("Patch / vulnerability management", "ID.RA-08"),
]


def import_csf(session) -> m.Framework:
    framework = m.Framework(
        name=FRAMEWORK_NAME,
        version=CSF_VERSION,
        effective_date=CSF_EFFECTIVE_DATE,
        licence_tier="public",
        source_url=CSF_SOURCE_URL,
        retired=False,
    )
    session.add(framework)
    session.flush()

    category_controls: dict[str, m.FrameworkControl] = {}
    for category_id, _function_id, short_title in CSF_CATEGORIES:
        fc = m.FrameworkControl(
            framework_id=framework.id,
            control_id=category_id,
            short_title=short_title,
            parent_id=None,
            status="active",
            source_ref=CSF_SOURCE_URL,
        )
        session.add(fc)
        category_controls[category_id] = fc
    session.flush()

    subcategory_controls: dict[str, m.FrameworkControl] = {}
    for subcategory_id, category_id, short_title in CSF_SUBCATEGORIES:
        assert subcategory_id not in WITHDRAWN_CSF_1_1_IDS, (
            f"{subcategory_id} is a withdrawn CSF 1.1 ID and must not be imported"
        )
        parent = category_controls[category_id]
        fc = m.FrameworkControl(
            framework_id=framework.id,
            control_id=subcategory_id,
            short_title=short_title,
            parent_id=parent.id,
            status="active",
            source_ref=CSF_SOURCE_URL,
        )
        session.add(fc)
        subcategory_controls[subcategory_id] = fc
    session.flush()

    for rule_id, title, category, weight in STARTER_FINDING_RULES:
        if session.get(m.FindingRule, rule_id) is None:
            session.add(
                m.FindingRule(
                    rule_id=rule_id, title=title, category=category, default_severity_weight=weight
                )
            )
    session.flush()

    for rule_id, subcategory_id in STARTER_MAPPING_RULES:
        fc = subcategory_controls[subcategory_id]
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

    control_types_by_name = {
        ct.name: ct for ct in session.query(m.ControlType).all()
    }
    for control_type_name, subcategory_id in STARTER_MAPPING_CONTROL_TYPES:
        ct = control_types_by_name.get(control_type_name)
        if ct is None:
            continue  # control type not seeded yet in this DB; skip rather than fabricate an id
        fc = subcategory_controls[subcategory_id]
        session.add(
            m.ControlMapping(
                from_kind="control_type",
                from_id=ct.id,
                framework_control_id=fc.id,
                relationship_type="intersects",
                confidence=0.5,
                source="starter",
            )
        )

    return framework
