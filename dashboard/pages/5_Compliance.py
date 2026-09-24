"""Compliance and Framework Mapping (build-spec.md section 3.6, L1): NIST
CSF 2.0 heatmap by Function, computed from finding/control-coverage status
-- never typed in (CLAUDE.md rule 1)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.compliance.status import compliance_status
from app.data import models as m
from app.data.db import session_scope

st.set_page_config(page_title="Compliance | StochastiQ", layout="wide")
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
    "NIST CSF 2.0 Functions/Categories are corroborated against published sources; "
    "the Subcategory list here is a starter subset with paraphrased short titles, "
    "not yet verified against the live NIST CPRT tool (this environment's network "
    "policy currently blocks csrc.nist.gov -- see PLAN.md section 8). "
    "The finding-to-control mapping is a starter, unvalidated by an assessor."
)

rows = compliance_status(framework="NIST CSF", scope="org")
if not rows:
    st.info("No active subcategories found for this framework.")
    st.stop()

df = pd.DataFrame(rows)
df["function"] = df["control_id"].str.split(".").str[0]

status_order = {"gap": 0, "partial": 1, "met": 2, "unknown": 3}
df["status_rank"] = df["status"].map(status_order)

st.subheader("Status by Subcategory")
color_map = {"gap": "🔴", "partial": "🟡", "met": "🟢", "unknown": "⚪"}
df["status_display"] = df["status"].map(lambda s: f"{color_map.get(s, '')} {s}")
st.dataframe(
    df[["control_id", "short_title", "function", "status_display"]].sort_values(
        ["function", "control_id"]
    ),
    hide_index=True,
    width="stretch",
)

st.subheader("Heatmap by Function")
heatmap = (
    df.groupby(["function", "status"]).size().unstack(fill_value=0).reindex(columns=["gap", "partial", "met", "unknown"], fill_value=0)
)
st.dataframe(heatmap, width="stretch")

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
