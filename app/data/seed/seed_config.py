"""Distribution parameters for the synthetic demo company.

A tiny hand-written dataset (3 BUs, ~30 assets, 3 services, 8 scenarios).
Every parameter below carries a source note: synthetic inputs, real
mechanics, labeled which is which, and every distribution parameter in the
config has a source note.

The company itself (a mid-size Indian NBFC with a broking subsidiary) is
SYNTHETIC. The distribution shapes and anchor values below are drawn from
the published research in docs/research/loss-caliberation.md where noted;
everything else is a stated assumption (is_assumption=True).
"""

from __future__ import annotations

from dataclasses import dataclass

ORG_NAME = "Synthetic: Aranya Finance & Securities"  # fictional, synthetic
ORG_SECTOR = "financial_services"
ORG_ENTITY_TYPE = "NBFC+broker"  # exercises both RBI and SEBI layers
ORG_REVENUE_INR = 2_500_000_000.0  # ~INR 250 crore/year; mid-market band (assumption)
ORG_SIZE_BAND = "mid-market"

BUSINESS_UNITS = ["Lending Operations", "Broking Subsidiary", "Corporate IT"]

# Beta(a, b) for the hidden per-BU maturity variable. Stays generator-only,
# never enters the DB. Source: no verified public maturity distribution
# exists (loss-caliberation.md, "Not found" item); these shape parameters
# are an assumption chosen to give a realistic spread (mean ~0.55, moderate
# variance) across only 3 BUs.
MATURITY_BETA_A = 5.0
MATURITY_BETA_B = 4.0

# Patch latency: lognormal with median 43 days (DBIR 2026, via Tenable,
# secondary source per loss-caliberation.md section 4), scaled by (1 - maturity).
PATCH_LATENCY_MEDIAN_DAYS = 43.0
PATCH_LATENCY_SIGMA = 0.6  # assumption: moderate spread around the median

N_ASSETS_TARGET = 30
N_SERVICES_PER_BU = 1  # 3 BUs x 1 service each = 3 services total
N_SCENARIOS = 8

ASSET_TYPES = ["server", "workstation", "network_device", "database", "cloud_vm"]

# Heavy-tailed asset criticality/records: Pareto shape (assumption; asset
# counts, records and criticality are heavy-tailed).
RECORDS_PARETO_SHAPE = 1.5
RECORDS_SCALE = 1_000


@dataclass(frozen=True)
class ThreatScenarioSpec:
    name: str
    threat_community: str
    description: str
    # 90% CI (low, mode, high) per factor, with calibration_source/population/rationale.
    tef: tuple[float, float, float]
    vuln: tuple[float, float, float]
    plm: tuple[float, float, float]  # INR, illustrative (USD anchors x FX rate)
    slef: tuple[float, float, float]
    slm: tuple[float, float, float]
    calibration_source: str
    population: str
    rationale: str


# Loss anchors are illustrative USD figures from docs/research/loss-caliberation.md,
# converted at the single configurable FX rate in app.config (labeled
# illustrative). Frequencies use Coalition's 1.54% all-event claims rate as
# a segment anchor (secondary source), NOT applied per-scenario at full
# value: each scenario gets a fraction of it, so that summed scenario
# frequencies stay consistent with the all-event anchor.
THREAT_SCENARIOS: list[ThreatScenarioSpec] = [
    ThreatScenarioSpec(
        name="Ransomware on lending core systems",
        threat_community="organized_crime",
        description="Encryption + extortion against loan-origination/servicing systems.",
        tef=(0.10, 0.20, 0.40),
        vuln=(0.10, 0.25, 0.45),
        plm=(2_000_000.0, 12_000_000.0, 60_000_000.0),  # INR; anchor: Coalition ransomware $269K x FX, scaled up for a core-system event
        slef=(0.2, 0.4, 0.6),
        slm=(500_000.0, 3_000_000.0, 15_000_000.0),
        calibration_source="Coalition 2026 Cyber Claims Report (ransomware avg $269K, secondary)",
        population="insured_smb_claims",
        rationale="Core-system ransomware scaled above the SMB claims average because lending "
        "systems are higher-value targets; TEF kept low given no direct incident history.",
    ),
    ThreatScenarioSpec(
        name="Business email compromise / fraudulent transfer",
        threat_community="organized_crime",
        description="Social-engineering-driven fraudulent payment instruction.",
        tef=(0.15, 0.30, 0.55),
        vuln=(0.15, 0.30, 0.50),
        plm=(500_000.0, 2_500_000.0, 12_000_000.0),
        slef=(0.05, 0.15, 0.30),
        slm=(100_000.0, 500_000.0, 2_000_000.0),
        calibration_source="Coalition 2026 Cyber Claims Report (BEC avg $27K, FTF avg $141K)",
        population="insured_smb_claims",
        rationale="BEC/FTF are the highest-frequency, lower-severity Coalition categories; "
        "PLM scaled to INR mid-market transfer sizes.",
    ),
    ThreatScenarioSpec(
        name="Exposed customer data store (KYC/PII)",
        threat_community="opportunistic_attacker",
        description="Misconfigured storage or DB exposing KYC/PII records.",
        tef=(0.08, 0.18, 0.35),
        vuln=(0.10, 0.20, 0.40),
        plm=(1_000_000.0, 6_000_000.0, 30_000_000.0),
        slef=(0.4, 0.6, 0.8),
        slm=(2_000_000.0, 10_000_000.0, 50_000_000.0),
        calibration_source="Cyentia IRIS 2025 (median ~$3M, P95 $32M, publicly reported events)",
        population="publicly_reported_events",
        rationale="Secondary-loss heavy given DPDP/SEBI notification and reputational exposure "
        "for a regulated financial entity holding KYC data.",
    ),
    ThreatScenarioSpec(
        name="Unpatched internet-facing CVE exploitation (KEV)",
        threat_community="opportunistic_attacker",
        description="Exploitation of a KEV-listed CVE on an internet-facing asset.",
        tef=(0.20, 0.40, 0.70),
        vuln=(0.20, 0.40, 0.65),
        plm=(500_000.0, 3_000_000.0, 15_000_000.0),
        slef=(0.15, 0.30, 0.50),
        slm=(200_000.0, 1_500_000.0, 8_000_000.0),
        calibration_source="CISA KEV catalog (real feed) + DBIR 2026 (exploitation 31% of initial access)",
        population="real_vuln_intel",
        rationale="TEF/Vuln driven by ExposureMult from real KEV/EPSS data once Task 8 lands; "
        "these are the pre-telemetry priors.",
    ),
    ThreatScenarioSpec(
        name="Insider misuse of privileged access",
        threat_community="malicious_insider",
        description="Privileged account used to exfiltrate or tamper with data.",
        tef=(0.03, 0.08, 0.18),
        vuln=(0.10, 0.25, 0.45),
        plm=(300_000.0, 2_000_000.0, 10_000_000.0),
        slef=(0.1, 0.25, 0.45),
        slm=(100_000.0, 800_000.0, 4_000_000.0),
        calibration_source="Assumption (no verified public insider-frequency source found)",
        population="assumption",
        rationale="Low TEF reflecting rarity of confirmed insider events relative to external "
        "threats in published claims data; kept as an explicit assumption.",
    ),
    ThreatScenarioSpec(
        name="Third-party / vendor compromise",
        threat_community="organized_crime",
        description="Compromise via an outsourced IT or vendor connection.",
        tef=(0.05, 0.12, 0.25),
        vuln=(0.15, 0.30, 0.50),
        plm=(500_000.0, 3_000_000.0, 18_000_000.0),
        slef=(0.2, 0.35, 0.55),
        slm=(300_000.0, 1_500_000.0, 6_000_000.0),
        calibration_source="DBIR 2026 (third-party involvement in 48% of breaches, +60% YoY)",
        population="dbir_2026",
        rationale="Rising third-party involvement trend used to justify a non-trivial TEF "
        "despite no direct incident history.",
    ),
    ThreatScenarioSpec(
        name="Distributed denial of service on trading/broking platform",
        threat_community="hacktivist",
        description="Availability attack against the broking subsidiary's trading platform.",
        tef=(0.05, 0.12, 0.30),
        vuln=(0.30, 0.50, 0.75),
        plm=(200_000.0, 1_200_000.0, 6_000_000.0),
        slef=(0.05, 0.10, 0.20),
        slm=(50_000.0, 300_000.0, 1_500_000.0),
        calibration_source="Assumption, scaled from BUSINESS_SERVICE.downtime_cost_per_hour",
        population="assumption",
        rationale="Primary loss should ultimately be derived from the broking service's own "
        "downtime cost rather than an independent PLM prior; kept as a starting range.",
    ),
    ThreatScenarioSpec(
        name="Cloud misconfiguration (IAM / storage)",
        threat_community="opportunistic_attacker",
        description="Overly permissive IAM role or public cloud storage bucket.",
        tef=(0.10, 0.22, 0.40),
        vuln=(0.15, 0.30, 0.50),
        plm=(400_000.0, 2_500_000.0, 12_000_000.0),
        slef=(0.2, 0.35, 0.55),
        slm=(200_000.0, 1_000_000.0, 5_000_000.0),
        calibration_source="OSV/GitHub Advisories + CIS Controls v8.1 (Control 4: Secure Configuration)",
        population="real_vuln_intel",
        rationale="Cloud misconfig findings map cleanly to CIS Control 4 / ISO A.8.9 for the "
        "compliance layer (Task 6), so this scenario doubles as a compliance demo hook.",
    ),
]

# Links each scenario to the controls that affect it, and which top-level
# factor they scale (O-RA section 5.5's four control categories). This is
# what makes apply_controls() move a scenario's EAL at all: without a row
# here, a control exists in the DB but has no effect on any scenario.
SCENARIO_CONTROL_LINKS: list[tuple[str, str, str]] = [
    ("Ransomware on lending core systems", "EDR coverage", "Vuln"),
    ("Ransomware on lending core systems", "Patch / vulnerability management", "Vuln"),
    ("Ransomware on lending core systems", "SIEM / monitoring", "SLEF"),
    ("Business email compromise / fraudulent transfer", "MFA on privileged accounts", "Vuln"),
    ("Exposed customer data store (KYC/PII)", "MFA on privileged accounts", "Vuln"),
    ("Exposed customer data store (KYC/PII)", "Network segmentation", "TEF"),
    ("Unpatched internet-facing CVE exploitation (KEV)", "Patch / vulnerability management", "Vuln"),
    ("Unpatched internet-facing CVE exploitation (KEV)", "EDR coverage", "Vuln"),
    ("Insider misuse of privileged access", "MFA on privileged accounts", "Vuln"),
    ("Insider misuse of privileged access", "SIEM / monitoring", "SLEF"),
    ("Third-party / vendor compromise", "Network segmentation", "TEF"),
    ("Third-party / vendor compromise", "MFA on privileged accounts", "Vuln"),
    ("Distributed denial of service on trading/broking platform", "Network segmentation", "TEF"),
    ("Cloud misconfiguration (IAM / storage)", "Patch / vulnerability management", "Vuln"),
    ("Cloud misconfiguration (IAM / storage)", "MFA on privileged accounts", "Vuln"),
]
