"""Technical dashboard (build-spec.md section 3.5, L1): finding and asset
tables with filters, remediation backlog with ageing.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.data import models as m
from app.data.db import session_scope
from app.optimize.recommendations import top_finding_recommendations
from dashboard.theme import STATUS, inject_page_css

st.set_page_config(page_title="Technical | StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
st.title("Technical View")

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
