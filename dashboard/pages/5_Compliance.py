"""Compliance and Framework Mapping (build-spec.md section 3.6, L1): NIST
CSF 2.0 heatmap by Function, computed from finding/control-coverage status
-- never typed in (CLAUDE.md rule 1)."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.compliance.incident_clock import compute_incident_clocks
from app.compliance.status import compliance_status
from app.data import models as m
from app.data.db import session_scope
from dashboard.theme import STATUS, apply_layout, inject_page_css, status_badge_html

st.set_page_config(page_title="Compliance | StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
st.title("Compliance and Framework Mapping")

with session_scope() as session:
    frameworks = session.query(m.Framework).all()

if not frameworks:
    st.info(
        "No frameworks imported yet. Run `make seed` -- NIST CSF 2.0 import happens "
        "as part of the seed step (PLAN.md Task 6)."
    )
    st.stop()

st.caption(
    "All 6 Functions, 22 Categories and 106 Subcategories are NIST's own official "
    "CSF 2.0 OSCAL catalog (public domain), not a hand-typed subset. The "
    "finding-to-control mapping is still a starter, unvalidated by an assessor "
    "(build-spec.md risk R6)."
)

rows = compliance_status(framework="NIST CSF", scope="org")
if not rows:
    st.info("No active subcategories found for this framework.")
    st.stop()

df = pd.DataFrame(rows)
df["function"] = df["control_id"].str.split(".").str[0]

_STATUS_ORDER = ["gap", "partial", "met", "unknown"]
status_rank = {s: i for i, s in enumerate(_STATUS_ORDER)}
df["status_rank"] = df["status"].map(status_rank)

st.subheader("Heatmap by Function")
st.caption(
    "Status colors are reserved and never reused for anything else on this page "
    "(critical = gap, warning = partial, good = met, muted = unknown)."
)
heatmap = (
    df.groupby(["function", "status"])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=_STATUS_ORDER, fill_value=0)
)
heat_fig = go.Figure()
for status in _STATUS_ORDER:
    heat_fig.add_trace(
        go.Bar(
            name=status,
            y=heatmap.index,
            x=heatmap[status],
            orientation="h",
            marker_color=STATUS[status],
            hovertemplate=f"%{{y}} · {status}: %{{x}}<extra></extra>",
        )
    )
heat_fig.update_layout(barmode="stack", xaxis_title="Subcategories", yaxis={"autorange": "reversed"})
apply_layout(heat_fig, height=280, show_legend=True)
st.plotly_chart(heat_fig, width="stretch")

st.subheader("Status by Subcategory")
df["status_badge"] = df["status"].apply(status_badge_html)
display_df = df[["control_id", "short_title", "function", "status_badge"]].sort_values(
    ["function", "control_id"]
)
st.markdown(
    display_df.rename(
        columns={
            "control_id": "Control ID",
            "short_title": "Short title",
            "function": "Function",
            "status_badge": "Status",
        }
    ).to_html(escape=False, index=False),
    unsafe_allow_html=True,
)

st.subheader("Findings and their framework references")
with session_scope() as session:
    findings = session.query(m.Finding).filter(m.Finding.rule_id.isnot(None)).all()
    mappings = session.query(m.ControlMapping).filter_by(from_kind="finding_rule").all()
    controls = {c.id: c for c in session.query(m.FrameworkControl).all()}

mapping_by_rule: dict[str, list[str]] = {}
for mp in mappings:
    control = controls.get(mp.framework_control_id)
    if control:
        mapping_by_rule.setdefault(mp.from_id, []).append(control.control_id)

if findings:
    finding_rows = [
        {
            "rule_id": f.rule_id,
            "status": f.status,
            "framework_references": ", ".join(mapping_by_rule.get(f.rule_id, [])) or "(none mapped)",
            "mapping_source": "starter",
        }
        for f in findings
    ]
    st.dataframe(finding_rows, hide_index=True, width="stretch")
else:
    st.info("No findings yet.")

st.subheader("Indian Regulatory Catalogues (PLAN.md Task 17)")
st.caption(
    "RBI's 2026 Cybersecurity Directions and SEBI's CSCRF, hand-built from paragraph/"
    "standard IDs (never the regulator's full clause text, per CLAUDE.md's ISO/CIS "
    "licensing rule extended here). Every row below is honestly `verified=False`: "
    "sourced from secondary commentary in this pass, not confirmed against rbi.org.in "
    "or sebi.gov.in directly (see app/compliance/rbi_sebi_data.py's module docstring) "
    "-- shown as a red ⚠️ badge rather than silently promoted for demo polish."
)
with session_scope() as session:
    reg_frameworks = [
        f
        for f in session.query(m.Framework).all()
        if f.name != "NIST CSF"
    ]
    reg_controls = (
        session.query(m.FrameworkControl)
        .filter(m.FrameworkControl.framework_id.in_([f.id for f in reg_frameworks]))
        .all()
        if reg_frameworks
        else []
    )

if reg_frameworks:
    fw_by_id = {f.id: f.name for f in reg_frameworks}
    reg_df = pd.DataFrame(
        [
            {
                "Framework": fw_by_id[c.framework_id],
                "ID": c.control_id,
                "Short title": c.short_title,
                "Verified": "✅" if c.verified else "⚠️ unverified",
                "Source": c.source_ref,
            }
            for c in reg_controls
        ]
    ).sort_values(["Framework", "ID"])
    st.dataframe(reg_df, hide_index=True, width="stretch")
else:
    st.info("RBI/SEBI catalogues not imported yet. Run `make seed`.")

st.subheader("Incident-Clock Calculator")
st.caption(
    "Enter one detection timestamp; every applicable regulatory reporting deadline is "
    "computed from that single timestamp plus the ReportingObligation rows in the DB "
    "(DAKSH 6h, CERT-In 6h, SEBI 6h/24h/3d/7d/30d/75d, DPDP 72h). DPDP is gated on its "
    "13 May 2027 commencement date -- a detection before then shows 'not yet in force' "
    "rather than a real deadline."
)
detect_col, entity_col = st.columns(2)
with detect_col:
    detected_date = st.date_input("Detection date", value=dt.date(2026, 10, 1))
    detected_time = st.time_input("Detection time (UTC)", value=dt.time(9, 0))
with entity_col:
    entity_type = st.selectbox(
        "Entity type",
        ["bank", "nbfc", "market_infrastructure_institution", "intermediary", "data_fiduciary", "any_body_corporate"],
    )

detected_at = dt.datetime.combine(detected_date, detected_time, tzinfo=dt.UTC)
with session_scope() as session:
    clocks = compute_incident_clocks(session, detected_at, entity_type=entity_type)

if clocks:
    clock_df = pd.DataFrame(
        [
            {
                "Regime": c.regime,
                "Recipient": c.recipient,
                "Clock (hours)": c.clock_hours,
                "Deadline (UTC)": c.deadline.strftime("%Y-%m-%d %H:%M") if c.deadline else "—",
                "Status": "In force" if c.in_force else (c.note or "Not yet in force"),
                "Verified": "✅" if c.verified else "⚠️ unverified",
            }
            for c in clocks
        ]
    )
    st.dataframe(clock_df, hide_index=True, width="stretch")
else:
    st.info(f"No reporting obligations apply to entity type '{entity_type}'.")
