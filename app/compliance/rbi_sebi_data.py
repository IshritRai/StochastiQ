"""Hand-built RBI 2026 Directions + SEBI CSCRF catalogues (PLAN.md Task 17).

CLAUDE.md: "ISO/CIS: IDs and short titles only" -- extended here as this
project's own rule for any regulatory catalogue: paragraph/clause/standard
numbers and a short title, never the regulator's full clause text (both
RBI and SEBI publish their circulars for free, but reproducing them
verbatim here would still misrepresent a paraphrase as the primary source).

VERIFICATION STATUS (build-spec.md section 5's explicit gap), updated after
a follow-up primary-source pass on 2026-09-24:

- SEBI: the actual CSCRF circular (SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113,
  Aug 20, 2024, Annexure-1) was fetched and read in full from sebi.gov.in.
  It confirms RS.CO.S1's 6-hour email notification to SEBI/CERT-In and
  24-hour SEBI Incident Reporting Portal filing verbatim, and Annexure-O's
  Table 36 confirms the escalation ladder: interim report 3 days,
  mitigation measures 7 days, RCA report 30 days, forensic audit report up
  to 75 days (VAPT closure is a separate, 45-day track not modelled here).
  Every SEBI REPORTING_OBLIGATIONS row below is now `verified=True` against
  that primary text. The FIRE-format alignment circular
  (HO/(449)2026-ITD-5_DIV1/I/19448/2026, Aug 24 2026) was also confirmed to
  exist via sebi.gov.in but its full text (paragraph-level detail on any
  changed timelines) was not fetchable in this pass -- SEBI_CONTROLS rows
  sourced only from secondary commentary remain `verified=False`.
- RBI: the actual 2026 Direction was identified and its real circular
  number confirmed (RBI/DoS/2026-27/461, "RBI (Non-Banking Financial
  Companies - Cybersecurity, Technology: Risk, Resilience and Assurance
  Framework) Directions, 2026", issued 31 July 2026), but the PDF itself
  (rbidocs.rbi.org.in) sits behind a CAPTCHA that could not be passed in
  this pass, so the exact paragraph number for the DAKSH 6-hour reporting
  requirement is still unconfirmed against primary text. RBI_CONTROLS and
  the rbi_daksh REPORTING_OBLIGATIONS row remain `verified=False`.
- CERT-In's 6-hour requirement (cert_in row) is a standing 2022 direction
  under IT Act s.70B(6), independently well-established and kept
  `verified=True`.

Before a real demo: pass the RBI PDF through OCR/manual retrieval to get
past the CAPTCHA and confirm the exact DAKSH paragraph number, and fetch
the SEBI FIRE-format circular's full text if any of the SEBI_CONTROLS rows
need promoting.
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

# (regime, clock_hours, recipient, trigger, entity_types, effective_from, source_ref, verified)
# PLAN.md Task 17 done-when: "feeding one detection timestamp produces all
# clocks correctly, including DPDP showing 'not yet in force' before
# 13 May 2027." DPDP's effective_from gates its own clock in
# app/compliance/incident_clock.py.
#
# verified=True rows below were confirmed against the primary SEBI CSCRF
# circular (SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113, Aug 20 2024, fetched
# and read in full from sebi.gov.in on 2026-09-24) -- see this module's
# docstring for what was and wasn't confirmed.
REPORTING_OBLIGATIONS: list[tuple[str, float, str, str, list[str], dt.datetime | None, str, bool]] = [
    (
        "rbi_daksh",
        6.0,
        "RBI (via DAKSH platform)",
        "detection",
        ["bank", "nbfc"],
        RBI_EFFECTIVE_DATE,
        "https://www.bitscore.in/resources/rbi-cybersecurity-directions-2026",
        False,  # RBI/DoS/2026-27/461 PDF is CAPTCHA-gated; paragraph unconfirmed
    ),
    (
        "cert_in",
        6.0,
        "CERT-In",
        "detection",
        ["bank", "nbfc", "any_body_corporate"],
        dt.datetime(2022, 4, 28, tzinfo=dt.UTC),  # CERT-In direction under IT Act s.70B(6), 28 Apr 2022
        "https://ogma.in/blog/rbi-cybersecurity-directions-2026-commercial-banks-nbfc-audit",
        True,  # standing 2022 CERT-In direction, independently well-established
    ),
    (
        "sebi_email",
        6.0,
        "SEBI (designated email, mkt_incidents@sebi.gov.in)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html",
        True,  # CSCRF RS.CO.S1, confirmed verbatim from primary circular
    ),
    (
        "sebi_portal",
        24.0,
        "SEBI Incident Reporting Portal",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html",
        True,  # CSCRF RS.CO.S1, confirmed verbatim from primary circular
    ),
    (
        "sebi_interim",
        72.0,  # 3 days
        "SEBI Incident Reporting Portal (interim report)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html",
        True,  # CSCRF Annexure-O Table 36, confirmed from primary circular
    ),
    (
        "sebi_mitigation",
        168.0,  # 7 days
        "SEBI Incident Reporting Portal (mitigation measures)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html",
        True,  # CSCRF Annexure-O Table 36, confirmed from primary circular
    ),
    (
        "sebi_rca",
        720.0,  # 30 days
        "SEBI Incident Reporting Portal (root cause analysis)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html",
        True,  # CSCRF Annexure-O Table 36, confirmed from primary circular
    ),
    (
        "sebi_closure",
        1800.0,  # 75 days -- CSCRF Annexure-O Table 36's forensic-audit-report
        # deadline, confirmed from the primary circular; this is a distinct track
        # from VAPT closure (a separate 45-day requirement in CSCRF section 4.3,
        # not modelled as its own clock here).
        "SEBI Incident Reporting Portal (forensic audit report)",
        "detection",
        ["market_infrastructure_institution", "intermediary"],
        SEBI_EFFECTIVE_DATE,
        "https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html",
        True,  # CSCRF Annexure-O Table 36, confirmed from primary circular
    ),
    (
        "dpdp_breach",
        72.0,
        "Data Protection Board of India",
        "awareness",
        ["data_fiduciary"],
        dt.datetime(2027, 5, 13, tzinfo=dt.UTC),  # DPDP Rules commencement date
        "https://www.dpdpa.com/blogs/DPDPA_Implementation_Timeline.html",
        False,  # secondary-sourced; DPDP Rules text itself not fetched in this pass
    ),
]
