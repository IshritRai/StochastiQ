"""Compliance and Framework Mapping (build-spec.md section 3.6). Lands in
PLAN.md Task 6 (NIST CSF 2.0 import, starter mapping, computed
COMPLIANCE_STATUS heatmap). Placeholder only until real framework data is
imported -- no framework rows exist in the DB yet, so there's nothing to
display honestly (CLAUDE.md rule 1)."""

from __future__ import annotations

import streamlit as st

from app.data import models as m
from app.data.db import session_scope

st.set_page_config(page_title="Compliance | StochastiQ", layout="wide")
st.title("Compliance and Framework Mapping")

with session_scope() as session:
    frameworks = session.query(m.Framework).all()

if not frameworks:
    st.info(
        "No frameworks imported yet. NIST CSF 2.0 import and the starter "
        "finding-to-control mapping are PLAN.md Task 6."
    )
else:
    st.dataframe(
        [{"Framework": f.name, "Version": f.version, "Retired": f.retired} for f in frameworks],
        hide_index=True,
        width="stretch",
    )
