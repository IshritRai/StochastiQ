"""NIST CSF 2.0 structure: Functions, Categories, and a starter subset of
Subcategories.

PROVENANCE / VERIFICATION STATUS (read before extending this file):
- The 6 Functions and 22 Categories below are corroborated by
  docs/research/control_mapping.md section 1b and are used with reasonable
  confidence.
- The Subcategory list is NOT the full official 106. This environment's
  network policy currently blocks csrc.nist.gov (see PLAN.md section 8, item
  5, and the session's own note about this), so the authoritative NIST CPRT
  JSON/Excel could not be fetched. The subcategories below are a small,
  hand-picked subset -- exactly the ones docs/research/control_mapping.md's
  worked finding-to-control table (section 1e) already cites with a source
  trail -- and their short titles are PARAPHRASED from general knowledge of
  the published CSF 2.0 text, not transcribed verbatim (control_mapping.md's
  own recommendation #3: "ship only control IDs, your own paraphrased
  descriptions"). Treat every row here as unverified until checked against
  CPRT directly (csrc.nist.gov/projects/cprt) once network access allows it.
- Withdrawn CSF 1.1 IDs (e.g. PR.AC-x, DE.CM-8, RS.RP-01) are deliberately
  NOT included here, so there is nothing to filter at import time; the
  no-withdrawn-IDs guardrail test still checks this explicitly in case the
  list is ever extended with real CPRT data that includes them.
"""

from __future__ import annotations

import datetime as dt

CSF_VERSION = "2.0"
CSF_EFFECTIVE_DATE = dt.date(2024, 2, 26)
CSF_SOURCE_URL = "https://csrc.nist.gov/pubs/cswp/29/final"

CSF_FUNCTIONS: list[tuple[str, str]] = [
    ("GV", "Govern"),
    ("ID", "Identify"),
    ("PR", "Protect"),
    ("DE", "Detect"),
    ("RS", "Respond"),
    ("RC", "Recover"),
]

CSF_CATEGORIES: list[tuple[str, str, str]] = [
    # (category_id, function_id, short_title)
    ("GV.OC", "GV", "Organizational Context"),
    ("GV.RM", "GV", "Risk Management Strategy"),
    ("GV.RR", "GV", "Roles, Responsibilities & Authorities"),
    ("GV.PO", "GV", "Policy"),
    ("GV.OV", "GV", "Oversight"),
    ("GV.SC", "GV", "Cybersecurity Supply Chain Risk Management"),
    ("ID.AM", "ID", "Asset Management"),
    ("ID.RA", "ID", "Risk Assessment"),
    ("ID.IM", "ID", "Improvement"),
    ("PR.AA", "PR", "Identity Management, Authentication & Access Control"),
    ("PR.AT", "PR", "Awareness & Training"),
    ("PR.DS", "PR", "Data Security"),
    ("PR.PS", "PR", "Platform Security"),
    ("PR.IR", "PR", "Technology Infrastructure Resilience"),
    ("DE.CM", "DE", "Continuous Monitoring"),
    ("DE.AE", "DE", "Adverse Event Analysis"),
    ("RS.MA", "RS", "Incident Management"),
    ("RS.AN", "RS", "Incident Analysis"),
    ("RS.CO", "RS", "Incident Response Reporting & Communication"),
    ("RS.MI", "RS", "Incident Mitigation"),
    ("RC.RP", "RC", "Incident Recovery Plan Execution"),
    ("RC.CO", "RC", "Incident Recovery Communication"),
]

# Starter subset only -- see module docstring. (subcategory_id, category_id, paraphrased_short_title)
CSF_SUBCATEGORIES: list[tuple[str, str, str]] = [
    ("ID.AM-01", "ID.AM", "Hardware assets are inventoried"),
    ("ID.AM-02", "ID.AM", "Software, services, and systems are inventoried"),
    ("ID.AM-03", "ID.AM", "Network communication and data flows are mapped"),
    ("ID.RA-01", "ID.RA", "Asset vulnerabilities are identified and recorded"),
    ("ID.RA-08", "ID.RA", "Vulnerability disclosure intake and response is established"),
    ("PR.AA-01", "PR.AA", "Identities and credentials are issued and managed"),
    ("PR.AA-03", "PR.AA", "Users, services, and hardware are authenticated"),
    ("PR.AA-05", "PR.AA", "Access permissions follow least privilege and are reviewed"),
    ("PR.DS-01", "PR.DS", "Data-at-rest confidentiality/integrity/availability is protected"),
    ("PR.DS-02", "PR.DS", "Data-in-transit confidentiality/integrity/availability is protected"),
    ("PR.PS-01", "PR.PS", "Configuration management practices are established"),
    ("PR.PS-02", "PR.PS", "Software is patched, replaced, or removed per risk"),
    ("PR.PS-04", "PR.PS", "Logs are generated and available for monitoring"),
    ("PR.IR-01", "PR.IR", "Networks are protected from unauthorized access"),
    ("DE.CM-01", "DE.CM", "Networks and network services are monitored"),
    ("DE.CM-03", "DE.CM", "Personnel activity and technology usage are monitored"),
    ("DE.CM-09", "DE.CM", "Computing hardware/software/runtime is monitored"),
    ("DE.AE-03", "DE.AE", "Event information is correlated across sources"),
]

# Withdrawn CSF 1.1 IDs, kept here only so the "never appears" guardrail test
# has something concrete to assert against if this list is ever extended.
WITHDRAWN_CSF_1_1_IDS: frozenset[str] = frozenset(
    {
        "PR.AC-1", "PR.AC-2", "PR.AC-3", "PR.AC-4", "PR.AC-5", "PR.AC-6", "PR.AC-7",
        "DE.CM-8", "RS.RP-1",
    }
)
