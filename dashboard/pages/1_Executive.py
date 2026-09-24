"""Executive dashboard (build-spec.md section 3.5, L1):
EAL, VaR95, loss exceedance curve, top 5 scenarios, top contributors,
Enterprise Risk Score. Every figure traces to a run ID -- nothing here is
a literal constant (CLAUDE.md rule 1).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import attribute, run_org
from dashboard.format_utils import format_inr
from dashboard.theme import CATEGORICAL, INK_SECONDARY, apply_layout, inject_page_css

st.set_page_config(page_title="Executive | StochastiQ", layout="wide", page_icon="\U0001f6e1️")
st.markdown(inject_page_css(), unsafe_allow_html=True)
st.title("Executive Risk View")


@st.cache_data(ttl=300, show_spinner="Running the risk engine...")
def _load_org_run(seed: int, n_iter: int):
    org = run_org(overrides={"n_iter": n_iter}, seed=seed)
    attribution_rows = attribute(org.run_id)
    return org, attribution_rows


def _enterprise_risk_score(eal: float, revenue_inr: float) -> float:
    """Documented monotone mapping of EAL-as-share-of-revenue onto 0-100
    (build-spec.md section 3.5). ASSUMPTION: caps at 100 once EAL reaches
    5% of revenue -- there is no verified public calibration for this cap
    (PLAN.md section 7 lists the same gap for control efficacy); revisit
    once real loss history exists."""
    if revenue_inr <= 0:
        return 0.0
    share = eal / revenue_inr
    return float(min(100.0, (share / 0.05) * 100.0))


with session_scope() as _session:
    org_row = _session.query(m.Organization).first()
    org_revenue_inr = org_row.revenue_inr if org_row else None

if org_row is None:
    st.warning("No organization found. Run `make seed` to populate the database first.")
    st.stop()

org, attribution_rows = _load_org_run(settings.default_seed, settings.default_n_iter)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Expected Annual Loss (EAL)", format_inr(org.summary.eal))
col2.metric("VaR95 (95th percentile annual loss)", format_inr(org.summary.var95))
col3.metric("VaR99 (99th percentile annual loss)", format_inr(org.summary.var99))
score = _enterprise_risk_score(org.summary.eal, org_revenue_inr)
col4.metric("Enterprise Risk Score (0-100, illustrative)", f"{score:.0f}")

st.caption(
    f"Run ID: `{org.run_id}` · seed={org.seed} · n_iter={org.n_iter} · "
    f"engine v{next(iter(org.scenario_results.values())).engine_version if org.scenario_results else 'n/a'}. "
    "VaR is a percentile of simulated annual loss, not a regulatory VaR (build-spec.md section 1.4)."
)

st.subheader("Loss Exceedance Curve")
lec_df = pd.DataFrame(org.summary.lec_points, columns=["loss", "exceedance_probability"])
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=lec_df["loss"],
        y=lec_df["exceedance_probability"],
        mode="lines",
        line={"color": CATEGORICAL["blue"], "width": 2},
        fill="tozeroy",
        fillcolor="rgba(42, 120, 214, 0.08)",
        hovertemplate="Loss exceeds %{x:,.0f}<br>P = %{y:.2%}<extra></extra>",
    )
)
fig.update_layout(
    xaxis_title="Annual loss (INR)",
    yaxis_title="P(loss exceeds X)",
    yaxis_type="log",
)
apply_layout(fig, height=350)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Log-scaled y-axis: a loss exceedance curve's whole point is the thin, high-value tail, "
    "which a linear axis flattens into an invisible sliver near zero."
)

st.subheader("Top 5 Scenarios by EAL")
scenario_names = {}
with session_scope() as _session:
    for sid in org.scenario_results:
        scenario = _session.get(m.ThreatScenario, sid)
        scenario_names[sid] = scenario.name if scenario else sid

scenario_table = (
    pd.DataFrame(
        [
            {
                "Scenario": scenario_names[sid],
                "EAL": result.summary.eal,
                "EAL (formatted)": format_inr(result.summary.eal),
                "VaR95 (formatted)": format_inr(result.summary.var95),
            }
            for sid, result in org.scenario_results.items()
        ]
    )
    .sort_values("EAL", ascending=False)
    .head(5)
)

bar_col, table_col = st.columns([3, 2])
with bar_col:
    bar_fig = go.Figure(
        go.Bar(
            x=scenario_table["EAL"],
            y=scenario_table["Scenario"],
            orientation="h",
            marker_color=CATEGORICAL["blue"],
            text=scenario_table["EAL (formatted)"],
            textposition="outside",
            cliponaxis=False,
            textfont={"color": INK_SECONDARY},
            hovertemplate="%{y}<br>EAL: %{text}<extra></extra>",
        )
    )
    bar_fig.update_layout(
        xaxis_title="EAL (INR)",
        yaxis={"autorange": "reversed"},
        xaxis_range=[0, scenario_table["EAL"].max() * 1.25],
    )
    apply_layout(bar_fig, height=260)
    st.plotly_chart(bar_fig, width="stretch")
with table_col:
    st.dataframe(
        scenario_table[["Scenario", "EAL (formatted)", "VaR95 (formatted)"]],
        hide_index=True,
        width="stretch",
    )

st.subheader("Top Risk Contributors (assets)")
if attribution_rows:
    with session_scope() as _session:
        asset_names = {a.id: a.hostname for a in _session.query(m.Asset).all()}
    contrib_df = (
        pd.DataFrame(attribution_rows)
        .assign(Asset=lambda d: d["entity_id"].map(asset_names))
        .sort_values("eal_share", ascending=False)
        .head(10)
    )
    contrib_df["EAL share (formatted)"] = contrib_df["eal_share"].apply(format_inr)

    bar_col2, table_col2 = st.columns([3, 2])
    with bar_col2:
        contrib_sorted = contrib_df.sort_values("eal_share", ascending=True)
        contrib_fig = go.Figure(
            go.Bar(
                x=contrib_sorted["eal_share"],
                y=contrib_sorted["Asset"],
                orientation="h",
                marker_color=CATEGORICAL["blue"],
                hovertemplate="%{y}<br>EAL share: %{x:,.0f}<extra></extra>",
            )
        )
        contrib_fig.update_layout(xaxis_title="EAL share (INR)")
        apply_layout(contrib_fig, height=280)
        st.plotly_chart(contrib_fig, width="stretch")
    with table_col2:
        st.dataframe(contrib_df[["Asset", "EAL share (formatted)"]], hide_index=True, width="stretch")
else:
    st.info("No attribution rows yet.")

st.caption(
    "Company data is synthetic. The Monte Carlo math, vulnerability intelligence, "
    "and framework catalogues are real."
)
