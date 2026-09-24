"""Executive dashboard (build-spec.md section 3.5, L1):
EAL, VaR95, loss exceedance curve, top 5 scenarios, top contributors,
Enterprise Risk Score. Every figure traces to a run ID -- nothing here is
a literal constant (CLAUDE.md rule 1).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.compliance.risk_link import compliance_risk_eal
from app.config import settings
from app.data import models as m
from app.data.db import session_scope
from app.engine.contracts import attribute, run_org
from app.engine.trend import org_eal_trend
from dashboard.format_utils import format_inr
from dashboard.theme import (
    CATEGORICAL,
    INK_SECONDARY,
    apply_layout,
    page_header,
    section_header,
)

page_header(
    "Executive Risk View",
    "Expected Annual Loss, Value-at-Risk, the loss exceedance curve, and where risk concentrates.",
    icon="\U0001f3af",
    eyebrow="Executive",
)


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
col1.metric("Expected Annual Loss", format_inr(org.summary.eal), help="EAL: mean of the simulated annual loss distribution.")
col2.metric(
    "VaR95 (annual)",
    format_inr(org.summary.var95),
    help="95th percentile of simulated annual loss -- not a regulatory VaR.",
)
col3.metric(
    "VaR99 (annual)",
    format_inr(org.summary.var99),
    help="99th percentile of simulated annual loss -- not a regulatory VaR.",
)
score = _enterprise_risk_score(org.summary.eal, org_revenue_inr)
col4.metric(
    "Enterprise Risk Score",
    f"{score:.0f} / 100",
    help="Illustrative: EAL as a share of revenue, capped at 100 once EAL reaches 5% of revenue.",
)

st.caption(
    f"Run ID: `{org.run_id}` · seed={org.seed} · n_iter={org.n_iter} · "
    f"engine v{next(iter(org.scenario_results.values())).engine_version if org.scenario_results else 'n/a'}. "
    "VaR is a percentile of simulated annual loss, not a regulatory VaR (build-spec.md section 1.4)."
)

section_header("Loss Exceedance Curve", icon="\U0001f4c9")
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

section_header("Top 5 Scenarios by EAL", icon="\U0001f3c6")
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

section_header("Top Risk Contributors (assets)", icon="\U0001f5a5\ufe0f")
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

section_header("EAL Trend", icon="\U0001f4c8")
st.caption(
    "Every stored org-level run at this session's seed, in the order it was computed -- "
    "a real accumulation of runs over time, not a fabricated 12-week series (PLAN.md's "
    "cut line for Task 19's fuller history). Filtered to ONE seed so a step here reflects "
    "a real DB change (a new finding, a coverage change, a fresh `make fetch-vuln-intel`), "
    "never Monte Carlo re-roll noise (R3 guardrail: 'no seed-per-refresh noise')."
)
trend_rows = org_eal_trend(seed=settings.default_seed)
if len(trend_rows) >= 2:
    trend_df = pd.DataFrame(trend_rows)
    trend_fig = go.Figure(
        go.Scatter(
            x=trend_df["snapshot_at"],
            y=trend_df["eal"],
            mode="lines+markers",
            line_color=CATEGORICAL["blue"],
            hovertemplate="%{x|%Y-%m-%d %H:%M}<br>EAL: %{y:,.0f}<extra></extra>",
        )
    )
    trend_fig.update_layout(xaxis_title="Run snapshot time", yaxis_title="EAL (INR)")
    apply_layout(trend_fig, height=240)
    st.plotly_chart(trend_fig, width="stretch")
else:
    st.info(
        f"Only {len(trend_rows)} stored run(s) at seed={settings.default_seed} so far -- "
        "a trend needs at least 2. Reload this page after a DB change (new findings, "
        "control coverage, or a `make fetch-vuln-intel` refresh) to accumulate more."
    )

section_header("Risk-to-Compliance ₹ Link", icon="\U0001f517")
st.caption(
    "EAL attributable to each unmet (gap/partial) NIST CSF control, allocated by the "
    "same weighted-share method `attribute()` uses for assets: a control's share of "
    "open-finding severity / uncovered-control-type weight, of the total across all "
    "unmet mapped controls, times this run's EAL. Rows sum to exactly this run's EAL "
    "across the controls they cover -- never invented, always traceable to run "
    f"{org.run_id[:8]}."
)
risk_link_rows = compliance_risk_eal(org.run_id)
if risk_link_rows:
    link_df = pd.DataFrame(risk_link_rows)
    link_df["EAL at risk"] = link_df["eal_at_risk_inr"].apply(format_inr)
    st.dataframe(
        link_df[["control_id", "short_title", "status", "EAL at risk"]].rename(
            columns={"control_id": "Control ID", "short_title": "Short title", "status": "Status"}
        ),
        hide_index=True,
        width="stretch",
    )
else:
    st.info(
        "No gap/partial controls with a mapped, nonzero weight yet -- run the Compliance "
        "page first so ComplianceStatus rows exist, or check `make seed`'s starter mapping."
    )

st.caption(
    "Company data is synthetic. The Monte Carlo math, vulnerability intelligence, "
    "and framework catalogues are real."
)
