"""Shared visual theme for the dashboard, built from the validated reference
palette (Claude's dataviz skill, references/palette.md). Colors are declared
once here by role and reused everywhere -- no chart picks its own hex.

Categorical order and status colors are used exactly as validated (never
reordered, never repurposed); see the skill's palette.md for the CVD/contrast
checks each slot passed under `scripts/validate_palette.js`.
"""

from __future__ import annotations

# Categorical (identity), in the validated fixed order -- never cycled or reordered.
CATEGORICAL = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "green": "#008300",
    "violet": "#4a3aa7",
    "red": "#e34948",
}

# Sequential (magnitude): one hue, light -> dark.
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]

# Status palette (state): fixed roles, never reused for a plain series.
STATUS = {
    "met": "#0ca30c",  # good
    "partial": "#fab219",  # warning
    "gap": "#d03b3b",  # critical
    "unknown": "#898781",  # muted ink, not a status hue -- "no data" is not a state
}
STATUS_ICON = {"met": "✓", "partial": "◐", "gap": "✕", "unknown": "–"}

# Chart chrome & ink (light mode only -- this app doesn't ship a dark toggle yet).
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
CHART_SURFACE = "#fcfcfb"
PAGE_PLANE = "#f9f9f7"

FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def apply_layout(fig, *, height: int = 360, show_legend: bool = False):
    """Applies the shared chart chrome (ink, gridlines, font) to a Plotly figure."""
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor=CHART_SURFACE,
        plot_bgcolor=CHART_SURFACE,
        font={"family": FONT_FAMILY, "color": INK_PRIMARY, "size": 13},
        showlegend=show_legend,
        legend={"font": {"color": INK_SECONDARY}},
        hoverlabel={"bgcolor": "white", "font": {"family": FONT_FAMILY}},
    )
    fig.update_xaxes(
        gridcolor=GRIDLINE, linecolor=BASELINE, tickfont={"color": INK_MUTED}, title_font={"color": INK_SECONDARY}
    )
    fig.update_yaxes(
        gridcolor=GRIDLINE, linecolor=BASELINE, tickfont={"color": INK_MUTED}, title_font={"color": INK_SECONDARY}
    )
    return fig


def inject_page_css() -> str:
    """CSS for stat-tile-style st.metric() cards: a hairline border and the
    shared surface color, so the KPI row reads as one system across pages."""
    return f"""
    <style>
    [data-testid="stMetric"] {{
        background-color: {CHART_SURFACE};
        border: 1px solid {GRIDLINE};
        border-radius: 8px;
        padding: 14px 16px 10px 16px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {INK_SECONDARY};
    }}
    [data-testid="stMetricValue"] {{
        color: {INK_PRIMARY};
        font-variant-numeric: normal;
    }}
    .status-badge {{
        display: inline-block;
        border-radius: 999px;
        padding: 1px 9px;
        font-size: 0.85em;
        font-weight: 600;
        margin-right: 6px;
    }}
    </style>
    """


def status_badge_html(status: str) -> str:
    color = STATUS.get(status, INK_MUTED)
    icon = STATUS_ICON.get(status, "")
    # White text on the two darkest status hues, dark ink on the lighter ones,
    # so the badge itself always clears text contrast regardless of the
    # sub-3:1 status-vs-surface figures the skill documents (that number is
    # about the status hue against the page surface, not about text set
    # directly on a filled chip of that hue).
    text_color = "#ffffff" if status in ("met", "gap") else INK_PRIMARY
    return (
        f'<span class="status-badge" style="background-color:{color};color:{text_color};">'
        f"{icon} {status}</span>"
    )
