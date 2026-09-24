"""Compliance and Framework Mapping (build-spec.md section 3.6, L1): NIST
CSF 2.0 heatmap by Function, computed from finding/control-coverage status
-- never typed in (CLAUDE.md rule 1)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
