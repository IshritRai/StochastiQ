"""Mitigation recommendations (build-spec.md section 3.3, L1):
rank top remediation actions by a real, DB-derived risk score, then fill a
template with engine/DB numbers. No LLM at L1 -- Gemini narrative rewriting
lands in PLAN.md Task 16, with a check that every number it uses came from
here (build-spec.md risk R5).

Control-level ranking by ΔEAL per rupee reuses
app.optimize.optimizer.evaluate_options() directly (that already IS this
ranking); this module adds the finding-level "which specific things to fix
first" ranking build-spec.md section 3.3 also asks for -- what would be
"KEV-first patching" once Task 8's real KEV data lands, and severity-weight
first until then (labeled accordingly, not silently presented as KEV data
that doesn't exist yet).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.data import models as m
from app.data.db import session_scope


@dataclass
class FindingRecommendation:
    finding_id: str
    asset_hostname: str
    rule_or_cve: str
    severity_weight: float
    asset_criticality: float
    risk_score: float
    recommendation_text: str


def top_finding_recommendations(limit: int = 10) -> list[FindingRecommendation]:
    """Ranks open findings by severity_weight x asset_criticality (a
    documented proxy for risk contribution -- the real per-finding ΔEAL
    requires simulating each finding's removal individually, which Task 8's
    exposure-index work will make cheap; until then this proxy is explicit
    about being a proxy, never presented as a simulated number)."""
    with session_scope() as session:
        findings = session.query(m.Finding).filter_by(status="open").all()
        assets_by_id = {a.id: a for a in session.query(m.Asset).all()}
        rules_by_id = {r.rule_id: r for r in session.query(m.FindingRule).all()}
        vulns_by_id = {v.cve_id: v for v in session.query(m.Vulnerability).all()}

    scored = []
    for finding in findings:
        asset = assets_by_id.get(finding.asset_id)
        if asset is None:
            continue
        criticality = asset.criticality or 1.0
        risk_score = finding.severity_weight * criticality

        if finding.cve_id:
            label = finding.cve_id
            vuln = vulns_by_id.get(finding.cve_id)
            if vuln and vuln.in_kev:
                risk_score *= 2.0  # KEV-listed: weighted higher, per build-spec.md's "KEV-first"
                label += " (CISA KEV)"
        else:
            rule = rules_by_id.get(finding.rule_id)
            label = rule.title if rule else (finding.rule_id or "unknown finding")

        text = (
            f"Remediate '{label}' on {asset.hostname} "
            f"(severity weight {finding.severity_weight:.1f}, asset criticality {criticality:.1f}/5)."
        )
        scored.append(
            FindingRecommendation(
                finding_id=finding.id,
                asset_hostname=asset.hostname,
                rule_or_cve=label,
                severity_weight=finding.severity_weight,
                asset_criticality=criticality,
                risk_score=risk_score,
                recommendation_text=text,
            )
        )

    scored.sort(key=lambda r: r.risk_score, reverse=True)
    return scored[:limit]
