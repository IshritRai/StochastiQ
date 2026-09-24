"""Hand-built RBI 2026 Directions + SEBI CSCRF catalogues (PLAN.md Task 17).

CLAUDE.md: "ISO/CIS: IDs and short titles only" -- extended here as this
project's own rule for any regulatory catalogue: paragraph/clause/standard
numbers and a short title, never the regulator's full clause text (both
RBI and SEBI publish their circulars for free, but reproducing them
verbatim here would still misrepresent a paraphrase as the primary source).

VERIFICATION STATUS (build-spec.md section 5's explicit gap): every ID
below was researched via secondary sources (WebSearch over industry/legal
commentary sites, listed in `source_ref`) in this session, because the two
primary sites did not yield a directly fetchable, paragraph-numbered
document in this pass (rbi.org.in redirected to its homepage rather than
the specific Direction's page; sebi.gov.in's circular index required a
follow-up fetch not completed here). Per CLAUDE.md ("no hard-coded
outputs... if you cannot verify a number against the primary source, set
verified=False rather than guessing"), every row is `verified=False`.
This is not a downgrade from the L1 plan -- the build spec already listed
these exact numbers as unverified secondary-sourced facts (section 5) -- it
is this pass being explicit that the L2 sweep did not close that gap
either, rather than silently promoting them to "verified" for demo polish.
Before a real demo: open the actual RBI Direction PDF (rbi.org.in) and the
SEBI CSCRF master circular (sebi.gov.in) and flip each row to
verified=True only once its exact paragraph/standard number is confirmed
there.
"""

from __future__ import annotations

import datetime as dt

RBI_FRAMEWORK_NAME = "RBI Cybersecurity and IT Governance Directions, 2026"
RBI_VERSION = "2026"
RBI_EFFECTIVE_DATE = dt.datetime(2026, 7, 31, tzinfo=dt.UTC)
RBI_SOURCE_URL = "https://www.rbi.org.in/"  # generic RBI notifications index; the specific
# Direction's own page did not resolve to a stable direct URL in this session (see module docstring)

SEBI_FRAMEWORK_NAME = "SEBI Cybersecurity and Cyber Resilience Framework (CSCRF)"
SEBI_VERSION = "2024 (as amended, incl. 24 Aug 2026 FIRE-format alignment circular)"
SEBI_EFFECTIVE_DATE = dt.datetime(2024, 8, 20, tzinfo=dt.UTC)
SEBI_SOURCE_URL = "https://www.sebi.gov.in/"

# (control_id, short_title, source_ref) -- RBI 2026 Directions, paragraph-level.
# Secondary sources used: taxguru.in, kpmg.com/in, ogma.in, bitscore.in
# (see individual source_ref values), all accessed via WebSearch 2026-09-24.
RBI_CONTROLS: list[tuple[str, str, str]] = [
    (
        "RBI-2026-DAKSH-6H",
        "Report cyber incidents to RBI via the DAKSH platform within 6 hours of detection",
        "https://www.bitscore.in/resources/rbi-cybersecurity-directions-2026",
    ),
    (
        "RBI-2026-BOARD-GOV",
        "Board-level cyber risk governance framework and oversight",
        "https://rmaindia.org/rbi-cybersecurity-directions-2026-board-level-cyber-risk-governance-framework/",
    ),
    (
        "RBI-2026-PRIV-ACCESS",
        "Privileged access management for critical systems",
        "https://sectona.com/blogs/technology/rbi-cybersecurity-compliance/",
    ),
    (
        "RBI-2026-RESILIENCE",
        "Cyber resilience, technology risk and assurance practices",
        "https://kpmg.com/in/en/insights/2026/09/rbis-technology-focused-master-directions-issued-on-31-july-2026.html",
    ),
    (
        "RBI-2026-NBFC-SCOPE",
        "Cybersecurity and technology risk directions applicability to NBFCs",
        "https://taxguru.in/rbi/rbi-issues-nbfc-cybersecurity-technology-risk-directions-2026-governance-framework.html",
    ),
]

# (control_id, short_title, source_ref) -- SEBI CSCRF standards/annexures.
SEBI_CONTROLS: list[tuple[str, str, str]] = [
    (
        "SEBI-CSCRF-6H-EMAIL",
        "Email cyber incident notification to SEBI-designated address within 6 hours",
        "https://www.cybernx.com/sebi-cscrf-reporting-requirements/",
    ),
    (
        "SEBI-CSCRF-24H-PORTAL",
        "File cyber incident report on SEBI's Incident Reporting Portal within 24 hours",
        "https://www.corplawupdates.in/updates/sebi-cyber-incident-reporting-fire-format-2026",
    ),
    (
        "SEBI-CSCRF-ANNEX-O",
        "Forensic audit report per Annexure-O clause 3.4",
        "https://www.cybernx.com/incident-response-under-sebi-cscrf-a-practical-guide-for-regulated-entities/",
    ),
    (
        "SEBI-CSCRF-VAPT",
        "Incident-related VAPT and closure report",
        "https://veritect.ai/digital-data-ai-law/sebi-cscrf-compliance-playbook",
    ),
]

# (regime, clock_hours, recipient, trigger, entity_types, effective_from, source_ref)
# PLAN.md Task 17 done-when: "feeding one detection timestamp produces all
# clocks correctly, including DPDP showing 'not yet in force' before
# 13 May 2027." DPDP's effective_from gates its own clock in
# app/compliance/incident_clock.py.
REPORTING_OBLIGATIONS: list[tuple[str, float, str, str, list[str], dt.datetime | None, str]] = [
    (
        "rbi_daksh",
        6.0,
        "RBI (via DAKSH platform)",
        "detection",
        ["bank", "nbfc"],
        RBI_EFFECTIVE_DATE,
        "https://www.bitscore.in/resources/rbi-cybersecurity-directions-2026",
    ),
    (
        "cert_in",
        6.0,
        "CERT-In",
        "detection",
        ["bank", "nbfc", "any_body_corporate"],
        dt.datetime(2022, 4, 28, tzinfo=dt.UTC),  # CERT-In direction under IT Act s.70B(6), 28 Apr 2022
        "https://ogma.in/blog/rbi-cybersecurity-directions-2026-commercial-banks-nbfc-audit",
    ),
    (
        "sebi_email",
        6.0,
        "SEBI (designated email)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.cybernx.com/sebi-cscrf-reporting-requirements/",
    ),
    (
        "sebi_portal",
        24.0,
        "SEBI Incident Reporting Portal",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.corplawupdates.in/updates/sebi-cyber-incident-reporting-fire-format-2026",
    ),
    (
        "sebi_interim",
        72.0,  # 3 days
        "SEBI Incident Reporting Portal (interim report)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://gurucul.com/blog/gurucul-boosts-cyber-resilience-in-indias-financial-sector-under-sebi-cscrf/",
    ),
    (
        "sebi_mitigation",
        168.0,  # 7 days
        "SEBI Incident Reporting Portal (mitigation measures)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://gurucul.com/blog/gurucul-boosts-cyber-resilience-in-indias-financial-sector-under-sebi-cscrf/",
    ),
    (
        "sebi_rca",
        720.0,  # 30 days
        "SEBI Incident Reporting Portal (root cause analysis)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://gurucul.com/blog/gurucul-boosts-cyber-resilience-in-indias-financial-sector-under-sebi-cscrf/",
    ),
    (
        "sebi_closure",
        1800.0,  # 75 days, per PLAN.md Task 17's own spec; secondary sources found in this
        # session corroborate a 45-day closure/VAPT deadline, not 75 -- flagged as an
        # explicit discrepancy rather than silently reconciled (verified=False either way).
        "SEBI Incident Reporting Portal (closure / VAPT report)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://veritect.ai/digital-data-ai-law/sebi-cscrf-compliance-playbook",
    ),
    (
        "dpdp_breach",
        72.0,
        "Data Protection Board of India",
        "awareness",
        ["data_fiduciary"],
        dt.datetime(2027, 5, 13, tzinfo=dt.UTC),  # DPDP Rules commencement date
        "https://www.dpdpa.com/blogs/DPDPA_Implementation_Timeline.html",
    ),
]
