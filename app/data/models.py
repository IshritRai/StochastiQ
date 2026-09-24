"""SQLAlchemy ORM models implementing build-spec.md section 1 in full.

Build-tag comments (L1/L2/L3) mirror the spec's own table, section 1.3.
Every number that ends up on a dashboard traces back to a row here plus a
SIMULATION_RUN id (CLAUDE.md: "provenance on every number: source,
timestamp, run ID").
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Business context (L1)
# ---------------------------------------------------------------------------


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)  # NBFC, broker, bank
    revenue_inr: Mapped[float] = mapped_column(Float, nullable=False)
    size_band: Mapped[str] = mapped_column(String, nullable=False)

    business_units: Mapped[list[BusinessUnit]] = relationship(back_populates="organization")


class BusinessUnit(Base):
    __tablename__ = "business_unit"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("organization.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="business_units")
    services: Mapped[list[BusinessService]] = relationship(back_populates="business_unit")
    assets: Mapped[list[Asset]] = relationship(back_populates="business_unit")


class BusinessService(Base):
    __tablename__ = "business_service"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    bu_id: Mapped[str] = mapped_column(ForeignKey("business_unit.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    revenue_per_hour: Mapped[float] = mapped_column(Float, nullable=False)
    downtime_cost_per_hour: Mapped[float] = mapped_column(Float, nullable=False)
    max_tolerable_downtime_h: Mapped[float] = mapped_column(Float, nullable=False)
    records_held: Mapped[int] = mapped_column(Integer, default=0)

    business_unit: Mapped[BusinessUnit] = relationship(back_populates="services")


class AssetService(Base):
    """Many-to-many: which assets support which business services, weighted."""

    __tablename__ = "asset_service"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("asset.id"), nullable=False)
    service_id: Mapped[str] = mapped_column(ForeignKey("business_service.id"), nullable=False)
    dependency_weight: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1


# ---------------------------------------------------------------------------
# Inventory and exposure (L1)
# ---------------------------------------------------------------------------


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    bu_id: Mapped[str] = mapped_column(ForeignKey("business_unit.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    internet_facing: Mapped[bool] = mapped_column(Boolean, default=False)
    environment: Mapped[str] = mapped_column(String, default="prod")
    owner: Mapped[str | None] = mapped_column(String, nullable=True)  # nullable: realistic gaps
    data_sensitivity: Mapped[int] = mapped_column(Integer, default=1)  # 1..5
    records_held: Mapped[int] = mapped_column(Integer, default=0)
    criticality: Mapped[float | None] = mapped_column(Float, nullable=True)  # derived, cached
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    source: Mapped[str] = mapped_column(String, default="synthetic")

    business_unit: Mapped[BusinessUnit] = relationship(back_populates="assets")


class Software(Base):
    __tablename__ = "software"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    product: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    cpe: Mapped[str | None] = mapped_column(String, nullable=True)
    purl: Mapped[str | None] = mapped_column(String, nullable=True)


class AssetSoftware(Base):
    __tablename__ = "asset_software"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("asset.id"), nullable=False)
    software_id: Mapped[str] = mapped_column(ForeignKey("software.id"), nullable=False)
    seen_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    # How this link was established. "declared": a real asset inventory named
    # this vendor/product on this asset. "synthetic_no_inventory": the
    # synthetic assets have no real software inventory to match a real KEV
    # CVE's vendor/product against, so the link is an arbitrary sampled
    # placement -- match_confidence records that honestly rather than
    # implying a verified match (CLAUDE.md: label which parts are synthetic).
    match_basis: Mapped[str] = mapped_column(String, default="declared")
    match_confidence: Mapped[float] = mapped_column(Float, default=1.0)


class Account(Base):
    __tablename__ = "account"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    asset_or_system: Mapped[str] = mapped_column(String, nullable=False)
    is_privileged: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String, default="synthetic")


class Vulnerability(Base):
    """Catalogue record. Score precedence: CNA, then CISA-ADP, then NVD, then default prior."""

    __tablename__ = "vulnerability"

    cve_id: Mapped[str] = mapped_column(String, primary_key=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cvss_vector: Mapped[str | None] = mapped_column(String, nullable=True)
    score_source: Mapped[str] = mapped_column(String, default="default")  # cna|adp|nvd|default
    cwe: Mapped[str | None] = mapped_column(String, nullable=True)
    epss: Mapped[float | None] = mapped_column(Float, nullable=True)
    epss_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    epss_date: Mapped[dt.date | None] = mapped_column(DateTime, nullable=True)
    in_kev: Mapped[bool] = mapped_column(Boolean, default=False)
    kev_date_added: Mapped[dt.date | None] = mapped_column(DateTime, nullable=True)
    kev_ransomware_use: Mapped[str | None] = mapped_column(String, nullable=True)
    nvd_status: Mapped[str | None] = mapped_column(String, nullable=True)


class FindingRule(Base):
    """Anchor for framework mapping; a rule-based finding has no CVE."""

    __tablename__ = "finding_rule"

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    default_severity_weight: Mapped[float] = mapped_column(Float, default=1.0)


class Finding(Base):
    """An instance of a problem on a specific asset. Not the same as a Vulnerability."""

    __tablename__ = "finding"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("asset.id"), nullable=False)
    finding_type: Mapped[str] = mapped_column(String, nullable=False)  # cve|misconfig|iam|coverage_gap
    cve_id: Mapped[str | None] = mapped_column(ForeignKey("vulnerability.cve_id"), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("finding_rule.rule_id"), nullable=True)
    severity_weight: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String, default="open")
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    due_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    remediated_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_source.id"), nullable=True)


class AssetDependency(Base):
    """L3: blast radius. Table exists from day one; populated only if time allows."""

    __tablename__ = "asset_dependency"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    from_asset: Mapped[str] = mapped_column(ForeignKey("asset.id"), nullable=False)
    to_asset: Mapped[str] = mapped_column(ForeignKey("asset.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)


# ---------------------------------------------------------------------------
# Controls (L1)
# ---------------------------------------------------------------------------


class ControlType(Base):
    """O-RA control categories (avoidance/deterrent/resistive/responsive), not FAIR-CAM."""

    __tablename__ = "control_type"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    fair_category: Mapped[str] = mapped_column(String, nullable=False)
    factor_changed: Mapped[str] = mapped_column(String, nullable=False)  # CF|PoA|Vuln|PLM|SLEF|SLM
    efficacy_low: Mapped[float] = mapped_column(Float, nullable=False)
    efficacy_mode: Mapped[float] = mapped_column(Float, nullable=False)
    efficacy_high: Mapped[float] = mapped_column(Float, nullable=False)
    prior_source: Mapped[str] = mapped_column(String, nullable=False)
    is_assumption: Mapped[bool] = mapped_column(Boolean, default=True)


class ControlState(Base):
    """Measured control effectiveness input, from telemetry."""

    __tablename__ = "control_state"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    control_type_id: Mapped[str] = mapped_column(ForeignKey("control_type.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String, nullable=False)  # org|bu|asset_group id/label
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1
    config_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_tested: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    measured_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    evidence_source: Mapped[str] = mapped_column(String, default="synthetic")


class ControlOption(Base):
    """Candidate investment. Costs are user-editable assumptions."""

    __tablename__ = "control_option"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    control_type_id: Mapped[str] = mapped_column(ForeignKey("control_type.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    target_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    capex: Mapped[float] = mapped_column(Float, default=0.0)
    opex_per_year: Mapped[float] = mapped_column(Float, default=0.0)
    lifetime_years: Mapped[float] = mapped_column(Float, default=3.0)
    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded list
    exclusions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded list


# ---------------------------------------------------------------------------
# Risk model and results (L1)
# ---------------------------------------------------------------------------


class ThreatScenario(Base):
    __tablename__ = "threat_scenario"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    threat_community: Mapped[str] = mapped_column(String, nullable=False)
    scope_rule: Mapped[str] = mapped_column(Text, nullable=False)  # JSON rule, not a stored list
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ScenarioInput(Base):
    """90% confidence intervals with mandatory rationale (O-RA calibration)."""

    __tablename__ = "scenario_input"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("threat_scenario.id"), nullable=False)
    factor: Mapped[str] = mapped_column(String, nullable=False)  # TEF|Vuln|PLM|SLEF|SLM
    low: Mapped[float] = mapped_column(Float, nullable=False)
    mode: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    distribution: Mapped[str] = mapped_column(String, default="pert")
    confidence: Mapped[float] = mapped_column(Float, default=0.90)
    calibration_source: Mapped[str] = mapped_column(String, nullable=False)
    population: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String, default="synthetic")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    is_assumption: Mapped[bool] = mapped_column(Boolean, default=True)


class ScenarioControlEffect(Base):
    """The only place technical controls touch the money model."""

    __tablename__ = "scenario_control_effect"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("threat_scenario.id"), nullable=False)
    control_type_id: Mapped[str] = mapped_column(ForeignKey("control_type.id"), nullable=False)
    factor: Mapped[str] = mapped_column(String, nullable=False)
    effect_model: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "multiplicative"


class SimulationRun(Base):
    """One Monte Carlo run. `overrides` records what-if changes for apply_controls."""

    __tablename__ = "simulation_run"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str | None] = mapped_column(
        ForeignKey("threat_scenario.id"), nullable=True
    )  # null = org-level run
    snapshot_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    n_iter: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs_hash: Mapped[str] = mapped_column(String, nullable=False)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)
    eal: Mapped[float] = mapped_column(Float, nullable=False)
    var95: Mapped[float] = mapped_column(Float, nullable=False)
    var99: Mapped[float] = mapped_column(Float, nullable=False)
    eal_std_err: Mapped[float] = mapped_column(Float, nullable=False)
    lec_points: Mapped[dict] = mapped_column(JSON, default=dict)
    overrides: Mapped[dict] = mapped_column(JSON, default=dict)


class RiskAttribution(Base):
    __tablename__ = "risk_attribution"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("simulation_run.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)  # asset|bu|vuln|finding|control_gap
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    eal_share: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String, default="allocation")  # allocation|leave_one_out


# ---------------------------------------------------------------------------
# Decisions (L1)
# ---------------------------------------------------------------------------


class InvestmentPlan(Base):
    __tablename__ = "investment_plan"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    objective: Mapped[str] = mapped_column(String, default="minimize_eal")
    baseline_run_id: Mapped[str] = mapped_column(ForeignKey("simulation_run.id"), nullable=False)
    joint_delta_eal: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class PlanItem(Base):
    __tablename__ = "plan_item"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(ForeignKey("investment_plan.id"), nullable=False)
    option_id: Mapped[str] = mapped_column(ForeignKey("control_option.id"), nullable=False)
    standalone_delta_eal: Mapped[float] = mapped_column(Float, nullable=False)
    marginal_delta_eal: Mapped[float | None] = mapped_column(Float, nullable=True)
    rosi: Mapped[float] = mapped_column(Float, nullable=False)


class Incident(Base):
    """L2: feeds frequency updating and the incident-clock demo."""

    __tablename__ = "incident"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    detected_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    scenario_type: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, default="synthetic")  # synthetic|real


class IncidentLoss(Base):
    __tablename__ = "incident_loss"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.id"), nullable=False)
    loss_form: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)


class IncidentAsset(Base):
    """Link table: incidents affect assets (many-to-many)."""

    __tablename__ = "incident_asset"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.id"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("asset.id"), nullable=False)


# ---------------------------------------------------------------------------
# Compliance (L1, with L2 evidence/reporting tables)
# ---------------------------------------------------------------------------


class Framework(Base):
    __tablename__ = "framework"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "NIST CSF"
    version: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[dt.date | None] = mapped_column(DateTime, nullable=True)
    licence_tier: Mapped[str] = mapped_column(String, default="public")
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    retired: Mapped[bool] = mapped_column(Boolean, default=False)


class FrameworkControl(Base):
    """ISO/CIS: ID and short title only, per CLAUDE.md licensing rule."""

    __tablename__ = "framework_control"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    framework_id: Mapped[str] = mapped_column(ForeignKey("framework.id"), nullable=False)
    control_id: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "PR.AA-03"
    short_title: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")  # active|withdrawn
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    # PLAN.md Task 17: True only if this exact ID/title was confirmed by
    # directly reading the regulator's own primary-source page/PDF in this
    # session; False (the honest default) means it is sourced from
    # secondary commentary and must be checked before being relied on in a
    # demo (CLAUDE.md: never guess a number/ID; build-spec.md section 5).
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class ControlMapping(Base):
    __tablename__ = "control_mapping"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    from_kind: Mapped[str] = mapped_column(String, nullable=False)  # finding_rule|control_type
    from_id: Mapped[str] = mapped_column(String, nullable=False)
    framework_control_id: Mapped[str] = mapped_column(
        ForeignKey("framework_control.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String, default="equal")  # equal|subset|superset|intersects
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String, default="starter")
    validated_by: Mapped[str | None] = mapped_column(String, nullable=True)


class ComplianceStatus(Base):
    __tablename__ = "compliance_status"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    framework_control_id: Mapped[str] = mapped_column(
        ForeignKey("framework_control.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    status: Mapped[str] = mapped_column(String, nullable=False)  # met|partial|gap|unknown
    basis: Mapped[dict] = mapped_column(JSON, default=dict)


class EvidenceRecord(Base):
    """L2: hash-chained so tampering is detectable."""

    __tablename__ = "evidence_record"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    ref: Mapped[str] = mapped_column(String, nullable=False)
    captured_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    prev_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class ReportingObligation(Base):
    """L2: drives incident clocks (RBI DAKSH, CERT-In, SEBI, DPDP)."""

    __tablename__ = "reporting_obligation"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    regime: Mapped[str] = mapped_column(String, nullable=False)  # rbi_daksh|cert_in|sebi|dpdp
    entity_types: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded list
    clock_hours: Mapped[float] = mapped_column(Float, nullable=False)
    recipient: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)
    effective_from: Mapped[dt.date | None] = mapped_column(DateTime, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)  # see FrameworkControl.verified
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Operations (L1)
# ---------------------------------------------------------------------------


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # csv|api|synthetic
    licence_note: Mapped[str | None] = mapped_column(String, nullable=True)


class IngestRun(Base):
    __tablename__ = "ingest_run"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_source.id"), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    rows_in: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="running")
    rejection_log: Mapped[dict] = mapped_column(JSON, default=dict)
