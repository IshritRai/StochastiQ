"""`make seed`: builds the synthetic company from seed_config.py and one RNG seed.

Done-when (build-spec.md section 3.1 / PLAN.md Task 1):
    running this twice with the same seed gives identical data.

The hidden per-BU maturity variable stays local to this script and is never
written to the database or returned to callers (build-spec.md section 3.1:
"The maturity variable stays in the generator only and never enters the
database or the model").
"""

from __future__ import annotations

import datetime as dt
import json

import numpy as np

from app.compliance.csf_import import STARTER_FINDING_RULES, import_csf
from app.config import settings
from app.data import models as m
from app.data.db import engine, init_db, session_scope
from app.data.seed import seed_config as cfg


def _drop_all_and_recreate() -> None:
    m.Base.metadata.drop_all(bind=engine)
    init_db()


def _make_business_units(session, org: m.Organization) -> list[m.BusinessUnit]:
    bus = []
    for name in cfg.BUSINESS_UNITS:
        bu = m.BusinessUnit(org_id=org.id, name=name)
        session.add(bu)
        bus.append(bu)
    session.flush()
    return bus


def _make_services(session, bus: list[m.BusinessUnit], rng: np.random.Generator) -> list[m.BusinessService]:
    services = []
    for bu in bus:
        downtime_cost = float(rng.uniform(50_000, 400_000))  # INR/hour, assumption
        svc = m.BusinessService(
            bu_id=bu.id,
            name=f"{bu.name} core service",
            revenue_per_hour=downtime_cost * 0.6,
            downtime_cost_per_hour=downtime_cost,
            max_tolerable_downtime_h=float(rng.uniform(2, 24)),
            records_held=int(rng.pareto(cfg.RECORDS_PARETO_SHAPE) * cfg.RECORDS_SCALE) + 100,
        )
        session.add(svc)
        services.append(svc)
    session.flush()
    return services


def _make_assets(
    session, bus: list[m.BusinessUnit], services: list[m.BusinessService], maturity: dict[str, float], rng: np.random.Generator
) -> list[m.Asset]:
    assets = []
    n_per_bu = cfg.N_ASSETS_TARGET // len(bus)
    for bu in bus:
        m_score = maturity[bu.id]
        for i in range(n_per_bu):
            internet_facing = bool(rng.random() < 0.25)
            # Realistic missingness: correlated with low maturity (loss-caliberation.md section 4).
            owner_missing = rng.random() < (0.35 * (1 - m_score))
            criticality_raw = float(rng.pareto(1.2)) + 1.0
            asset = m.Asset(
                bu_id=bu.id,
                type=str(rng.choice(cfg.ASSET_TYPES)),
                hostname=f"{bu.name[:3].lower()}-{rng.choice(cfg.ASSET_TYPES)}-{i:03d}",
                internet_facing=internet_facing,
                environment="prod" if rng.random() < 0.7 else "staging",
                owner=None if owner_missing else f"owner-{bu.name.split()[0].lower()}-{i}",
                data_sensitivity=int(rng.integers(1, 6)),
                records_held=int(rng.pareto(cfg.RECORDS_PARETO_SHAPE) * cfg.RECORDS_SCALE),
                criticality=min(5.0, max(1.0, criticality_raw)),
                source="synthetic",
            )
            session.add(asset)
            assets.append((asset, bu))
    session.flush()

    # Link a subset of assets to their BU's service, with a dependency weight.
    for asset, bu in assets:
        svc = next(s for s in services if s.bu_id == bu.id)
        if rng.random() < 0.8:
            session.add(
                m.AssetService(
                    asset_id=asset.id,
                    service_id=svc.id,
                    dependency_weight=float(rng.uniform(0.2, 1.0)),
                )
            )
    session.flush()
    return [a for a, _ in assets]


def _make_control_types(session) -> dict[str, m.ControlType]:
    specs = [
        ("MFA on privileged accounts", "resistive", "Vuln", 0.60, 0.80, 0.95),
        ("EDR coverage", "resistive", "Vuln", 0.40, 0.65, 0.85),
        ("Network segmentation", "avoidance", "CF", 0.30, 0.55, 0.75),
        ("Patch / vulnerability management", "resistive", "Vuln", 0.35, 0.60, 0.85),
        ("SIEM / monitoring", "responsive", "SLEF", 0.20, 0.45, 0.70),
    ]
    out = {}
    for name, category, factor, lo, mode, hi in specs:
        ct = m.ControlType(
            name=name,
            fair_category=category,
            factor_changed=factor,
            efficacy_low=lo,
            efficacy_mode=mode,
            efficacy_high=hi,
            prior_source="PLAN.md section 7 (no verified public efficacy source found; assumption)",
            is_assumption=True,
        )
        session.add(ct)
        out[name] = ct
    session.flush()
    return out


def _make_control_states(session, bus: list[m.BusinessUnit], control_types: dict, maturity: dict, rng) -> None:
    for bu in bus:
        m_score = maturity[bu.id]
        for ct in control_types.values():
            # Coverage correlated with the hidden maturity score via a logistic link,
            # per loss-caliberation.md section 4 recommendation #1.
            coverage = 1.0 / (1.0 + np.exp(-6 * (m_score - 0.5)))
            coverage = float(np.clip(coverage + rng.normal(0, 0.05), 0.0, 1.0))
            session.add(
                m.ControlState(
                    control_type_id=ct.id,
                    scope=bu.id,
                    coverage_pct=coverage,
                    config_strength=float(rng.uniform(0.5, 1.0)),
                    evidence_source="synthetic",
                )
            )


def _make_control_options(session, control_types: dict, rng: np.random.Generator) -> None:
    for ct in control_types.values():
        session.add(
            m.ControlOption(
                control_type_id=ct.id,
                scope="org",
                target_coverage=0.95,
                capex=float(rng.uniform(500_000, 5_000_000)),
                opex_per_year=float(rng.uniform(100_000, 1_000_000)),
                lifetime_years=3.0,
            )
        )


def _make_scenarios(session) -> list[m.ThreatScenario]:
    scenarios = []
    for spec in cfg.THREAT_SCENARIOS:
        ts = m.ThreatScenario(
            name=spec.name,
            threat_community=spec.threat_community,
            scope_rule=json.dumps({"applies_to": "org"}),
            description=spec.description,
            active=True,
        )
        session.add(ts)
        scenarios.append((ts, spec))
    session.flush()

    for ts, spec in scenarios:
        for factor, (low, mode, high) in (
            ("TEF", spec.tef),
            ("Vuln", spec.vuln),
            ("PLM", spec.plm),
            ("SLEF", spec.slef),
            ("SLM", spec.slm),
        ):
            session.add(
                m.ScenarioInput(
                    scenario_id=ts.id,
                    factor=factor,
                    low=low,
                    mode=mode,
                    high=high,
                    distribution="pert",
                    confidence=0.90,
                    calibration_source=spec.calibration_source,
                    population=spec.population,
                    rationale=spec.rationale,
                    is_assumption=(spec.population == "assumption"),
                )
            )
    return [ts for ts, _ in scenarios]


def _make_scenario_control_effects(
    session, scenarios: list[m.ThreatScenario], control_types: dict[str, m.ControlType]
) -> None:
    scenarios_by_name = {ts.name: ts for ts in scenarios}
    for scenario_name, control_name, factor in cfg.SCENARIO_CONTROL_LINKS:
        ts = scenarios_by_name[scenario_name]
        ct = control_types[control_name]
        session.add(
            m.ScenarioControlEffect(
                scenario_id=ts.id,
                control_type_id=ct.id,
                factor=factor,
                effect_model="multiplicative",
            )
        )


def _make_sample_findings(session, assets: list[m.Asset], rng: np.random.Generator) -> None:
    """A handful of rule-based findings, so the compliance heatmap (Task 6)
    has a real mix of gap/met statuses to show rather than an all-unknown
    page. Roughly a third are pre-remediated so both statuses appear.

    `first_seen` is backdated (assumption: uniform 1-180 days ago) rather than
    left at the seed's own run time -- an "ageing" remediation backlog
    (dashboard's Technical page) is meaningless if every finding was
    discovered "now" (CLAUDE.md: no invented realism, but no invented
    freshness either)."""
    if not assets:
        return
    now = dt.datetime.now(dt.UTC)
    for rule_id, _title, _category, weight in STARTER_FINDING_RULES:
        n_findings = int(rng.integers(1, 4))
        chosen_assets = rng.choice(assets, size=min(n_findings, len(assets)), replace=False)
        for asset in chosen_assets:
            status = "remediated" if rng.random() < 0.35 else "open"
            age_days = int(rng.integers(1, 181))
            first_seen = (now - dt.timedelta(days=age_days)).replace(tzinfo=None)
            session.add(
                m.Finding(
                    asset_id=asset.id,
                    finding_type="misconfig" if rule_id != "missing_mfa" else "iam",
                    rule_id=rule_id,
                    severity_weight=weight,
                    status=status,
                    first_seen=first_seen,
                    last_seen=first_seen,
                    remediated_at=None,
                )
            )


def _make_data_source(session) -> m.DataSource:
    ds = m.DataSource(name="hand-written seed generator", kind="synthetic", licence_note=None)
    session.add(ds)
    session.flush()
    return ds


def seed(reset: bool = True) -> None:
    if reset:
        _drop_all_and_recreate()
    else:
        init_db()

    rng = np.random.default_rng(settings.default_seed)

    with session_scope() as session:
        org = m.Organization(
            name=cfg.ORG_NAME,
            sector=cfg.ORG_SECTOR,
            entity_type=cfg.ORG_ENTITY_TYPE,
            revenue_inr=cfg.ORG_REVENUE_INR,
            size_band=cfg.ORG_SIZE_BAND,
        )
        session.add(org)
        session.flush()

        bus = _make_business_units(session, org)

        # Hidden maturity: generator-local only, never persisted (build-spec.md section 3.1).
        maturity = {
            bu.id: float(rng.beta(cfg.MATURITY_BETA_A, cfg.MATURITY_BETA_B)) for bu in bus
        }

        services = _make_services(session, bus, rng)
        assets = _make_assets(session, bus, services, maturity, rng)
        control_types = _make_control_types(session)
        _make_control_states(session, bus, control_types, maturity, rng)
        _make_control_options(session, control_types, rng)
        scenarios = _make_scenarios(session)
        _make_scenario_control_effects(session, scenarios, control_types)
        import_csf(session)
        _make_sample_findings(session, assets, rng)
        _make_data_source(session)


if __name__ == "__main__":
    seed()
    print(f"Seeded database at {settings.database_url} with seed={settings.default_seed}")
