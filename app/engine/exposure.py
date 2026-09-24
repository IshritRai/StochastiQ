"""Telemetry-driven ExposureMult (previously an identity 1.0 placeholder
at L1).

`compute_exposure_mult` turns the org's currently-open findings into a
single multiplier on the Vuln factor: findings on real CVEs that are in
CISA's KEV catalog, and/or carry a high EPSS score, count for more than a
plain misconfig finding. The raw score is UNBOUNDED by construction (it is
a literal average of real severity/KEV/EPSS weights, so a genuinely bad
telemetry snapshot can and should push it far from 1.0); the hard bound
(EAL must not swing arbitrarily because of one extreme finding) is
enforced downstream, in `risk_contract._apply_exposure_mult`'s
`np.clip(..., exposure_mult_lo, exposure_mult_hi)`, which is the ONE
place the bound is applied. This module never clips itself, so the
guardrail test (tests/test_exposure_guardrail.py) is a genuine end-to-end
check of that one clip, not a test of a second, possibly-inconsistent
bound here.

`is_assumption=True`-flavoured design choices:
- KEV membership doubles a finding's weight (`kev_multiplier`).
- EPSS score adds up to another 1x on top of the base weight (a finding
  with epss=1.0 is worth 2x its severity_weight; epss=0 adds nothing).
- The neutral baseline (exposure_mult == 1.0) is "the average open finding
  looks like a severity_weight=1.0 finding with no KEV/EPSS boost", i.e.
  a scenario with no open findings at all, or whose open findings average
  out to exactly that, gets no exposure adjustment.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.data import models as m

KEV_MULTIPLIER = 2.0


@dataclass
class ExposureBreakdown:
    exposure_mult_raw: float  # unbounded; the caller (_apply_exposure_mult) clips it
    n_open_findings: int
    n_kev_findings: int
    avg_epss: float | None


def _finding_weight(finding: m.Finding, vuln: m.Vulnerability | None) -> float:
    weight = finding.severity_weight
    if vuln is not None:
        if vuln.in_kev:
            weight *= KEV_MULTIPLIER
        if vuln.epss is not None:
            weight *= 1.0 + vuln.epss
    return weight


def compute_exposure_mult(session) -> ExposureBreakdown:
    """Org-wide, not scenario-scoped: ThreatScenario.scope_rule is a free-form
    JSON rule (not a structured asset filter this schema can query), so this
    L2 pass uses the same telemetry (all currently-open findings) for
    every scenario. Documented L2 simplification; a per-scenario asset scope
    is a natural L3 follow-up once scope_rule gains a queryable structure."""
    findings = session.query(m.Finding).filter(m.Finding.status == "open").all()
    if not findings:
        return ExposureBreakdown(exposure_mult_raw=1.0, n_open_findings=0, n_kev_findings=0, avg_epss=None)

    vuln_ids = {f.cve_id for f in findings if f.cve_id}
    vulns = {
        v.cve_id: v
        for v in session.query(m.Vulnerability).filter(m.Vulnerability.cve_id.in_(vuln_ids)).all()
    } if vuln_ids else {}

    weights = [_finding_weight(f, vulns.get(f.cve_id)) for f in findings]
    n_kev = sum(1 for f in findings if f.cve_id and vulns.get(f.cve_id) and vulns[f.cve_id].in_kev)
    epss_values = [vulns[f.cve_id].epss for f in findings if f.cve_id and vulns.get(f.cve_id) and vulns[f.cve_id].epss is not None]

    avg_weight = sum(weights) / len(weights)
    return ExposureBreakdown(
        exposure_mult_raw=avg_weight,
        n_open_findings=len(findings),
        n_kev_findings=n_kev,
        avg_epss=(sum(epss_values) / len(epss_values)) if epss_values else None,
    )
