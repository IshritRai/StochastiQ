"""Technical dashboard (build-spec.md section 3.5, L1): finding and asset
tables with filters, remediation backlog with ageing.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import run_org
from app.optimize.recommendations import top_finding_recommendations
from dashboard.format_utils import format_inr
from dashboard.theme import CATEGORICAL, INK_SECONDARY, STATUS, apply_layout, inject_page_css

st.set_page_config(page_title="Technical | StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
st.title("Technical View")


@st.cache_data(ttl=300, show_spinner="Running the risk engine...")
def _load_org_run(seed: int, n_iter: int):
    return run_org(overrides={"n_iter": n_iter}, seed=seed)

with session_scope() as session:
    assets = session.query(m.Asset).all()
    findings = session.query(m.Finding).all()
    hostnames = {a.id: a.hostname for a in assets}

    asset_rows = [
        {
            "hostname": a.hostname,
            "type": a.type,
            "internet_facing": a.internet_facing,
            "environment": a.environment,
            "owner": a.owner or "(unassigned)",
            "criticality": round(a.criticality, 2) if a.criticality else None,
            "data_sensitivity": a.data_sensitivity,
        }
        for a in assets
    ]
    finding_rows = [
        {
            "hostname": hostnames.get(f.asset_id, f.asset_id),
            "finding_type": f.finding_type,
            "cve_id": f.cve_id,
            "severity_weight": f.severity_weight,
            "status": f.status,
            "first_seen": f.first_seen,
            "age_days": (dt.datetime.now(dt.UTC) - f.first_seen.replace(tzinfo=dt.UTC)).days,
        }
        for f in findings
    ]

st.subheader("Asset Inventory")
if asset_rows:
    asset_df = pd.DataFrame(asset_rows)
    env_filter = st.multiselect("Environment", sorted(asset_df["environment"].unique()), default=list(asset_df["environment"].unique()))
    internet_only = st.checkbox("Internet-facing only", value=False)
    filtered = asset_df[asset_df["environment"].isin(env_filter)]
    if internet_only:
        filtered = filtered[filtered["internet_facing"]]
    st.dataframe(filtered, hide_index=True, width="stretch")
    st.caption(f"{len(filtered)} of {len(asset_df)} assets shown.")
else:
    st.info("No assets found. Run `make seed` to populate the database.")

st.subheader("Remediation Backlog (open findings, by age)")
if finding_rows:
    finding_df = pd.DataFrame(finding_rows)
    open_df = finding_df[finding_df["status"] == "open"].sort_values("age_days", ascending=False)
    st.dataframe(open_df, hide_index=True, width="stretch")
else:
    st.info(
        "No findings yet -- the real vulnerability intelligence and CSV importer "
        "land in PLAN.md Tasks 8-9. This table will populate once findings exist."
    )

st.subheader("Top Remediation Actions")
st.caption(
    "Ranked by severity weight x asset criticality, with real CISA KEV-listed CVEs "
    "weighted higher ('KEV-first patching', build-spec.md section 3.3). Run "
    "`make fetch-vuln-intel` to pull the current KEV catalog and EPSS scores "
    "(PLAN.md Task 8) -- this is a proxy risk score, not a simulated ΔEAL, "
    "labeled as such rather than presented as more precise than it is."
)
recommendations = top_finding_recommendations(limit=10)
if recommendations:
    rec_df = pd.DataFrame(
        [
            {
                "Recommendation": (
                    r.recommendation_text.replace(
                        "(CISA KEV)",
                        f'<span class="status-badge" style="background-color:{STATUS["gap"]};color:#fff;">KEV</span>',
                    )
                ),
                "Risk score": round(r.risk_score, 2),
            }
            for r in recommendations
        ]
    )
    st.markdown(rec_df.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info("No open findings to recommend against.")

st.subheader("Scenario Sensitivity & Stability (PLAN.md Task 15)")
st.caption(
    "Telemetry-driven ExposureMult: the Vuln factor is scaled by the current open-finding "
    "population (KEV-listed and high-EPSS CVEs weigh more), clipped to "
    f"[{settings.exposure_mult_lo}x, {settings.exposure_mult_hi}x] so no single finding can push "
    "EAL past that bound (build-spec.md risk R1's guardrail -- see "
    "tests/test_exposure_guardrail.py). The tornado chart perturbs each factor by "
    f"±{int(settings.tornado_perturbation_pct * 100)}% one at a time (same random draws each "
    "time, per build-spec.md's common-random-numbers rule) to show which factor's uncertainty "
    "moves EAL the most."
)

with session_scope() as session:
    scenario_names = {s.id: s.name for s in session.query(m.ThreatScenario).filter_by(active=True).all()}

org = _load_org_run(settings.default_seed, settings.default_n_iter)

if org.scenario_results:
    scenario_options = {scenario_names.get(sid, sid): sid for sid in org.scenario_results}
    chosen_name = st.selectbox("Scenario", sorted(scenario_options.keys()))
    chosen = org.scenario_results[scenario_options[chosen_name]]

    badge_col, exposure_col = st.columns(2)
    with badge_col:
        flags = []
        if chosen.stability and chosen.stability.get("fragile"):
            flags.append("🔶 **Fragile** — one factor's swing alone moves EAL more than "
                          f"{int(settings.fragile_swing_threshold * 100)}%")
        if chosen.stability and chosen.stability.get("unstable"):
            flags.append("🔷 **Unstable** — Monte Carlo std error exceeds "
                          f"{int(settings.unstable_stderr_threshold * 100)}% of EAL; consider more iterations")
        if not flags:
            st.success("Stable: neither Fragile nor Unstable at current thresholds.")
        for flag in flags:
            st.warning(flag)
    with exposure_col:
        st.metric(
            "ExposureMult (clipped)",
            f"{chosen.exposure_mult:.2f}x",
            help="1.0x = neutral (no open findings, or findings averaging the neutral baseline).",
        )
        if chosen.exposure_mult_clipped:
            st.caption("⚠️ Raw telemetry-derived value was clipped to the configured bound.")
        if chosen.exposure_breakdown:
            eb = chosen.exposure_breakdown
            st.caption(
                f"{eb['n_open_findings']} open findings ({eb['n_kev_findings']} KEV-listed), "
                f"run {chosen.run_id[:8]}"
            )

    if chosen.stability and chosen.stability.get("tornado"):
        tornado_df = pd.DataFrame(chosen.stability["tornado"])
        tornado_fig = go.Figure()
        for _, row in tornado_df.iterrows():
            tornado_fig.add_trace(
                go.Bar(
                    x=[row["eal_at_high"] - row["eal_at_low"]],
                    y=[row["factor"]],
                    base=[row["eal_at_low"]],
                    orientation="h",
                    marker_color=CATEGORICAL["blue"],
                    showlegend=False,
                    hovertemplate=(
                        f"{row['factor']}<br>Low: {format_inr(row['eal_at_low'])}"
                        f"<br>High: {format_inr(row['eal_at_high'])}<extra></extra>"
                    ),
                )
            )
        tornado_fig.update_layout(
            xaxis_title="EAL (INR) across ±"
            f"{int(settings.tornado_perturbation_pct * 100)}% perturbation",
            yaxis_title=None,
            font_color=INK_SECONDARY,
        )
        apply_layout(tornado_fig, height=260)
        st.plotly_chart(tornado_fig, width="stretch")
        st.caption(f"EAL at baseline: {format_inr(chosen.summary.eal)} (run {chosen.run_id[:8]}).")
else:
    st.info("No active scenarios found.")
