"""Shared visual theme for the dashboard, built from the validated reference
palette (Claude's dataviz skill, references/palette.md). Colors are declared
once here by role and reused everywhere -- no chart picks its own hex.

Categorical order and status colors are used exactly as validated (never
reordered, never repurposed); see the skill's palette.md for the CVD/contrast
checks each slot passed under `scripts/validate_palette.js`.

This module also carries the page-chrome layer (typography, spacing, card
surfaces, header component) so every page reads as one system rather than
five independently-styled Streamlit defaults.
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

# Brand accent -- the categorical "blue" slot, reused as the one accent color
# for chrome (links, active nav, focus rings) so chrome and charts read as
# the same system rather than two unrelated palettes.
ACCENT = CATEGORICAL["blue"]
ACCENT_SOFT = "rgba(42, 120, 214, 0.10)"
ACCENT_SOFT_BORDER = "rgba(42, 120, 214, 0.28)"

FONT_FAMILY = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_FAMILY_MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"


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
        hoverlabel={
            "bgcolor": "white",
            "font": {"family": FONT_FAMILY},
            "bordercolor": GRIDLINE,
        },
    )
    fig.update_xaxes(
        gridcolor=GRIDLINE, linecolor=BASELINE, tickfont={"color": INK_MUTED}, title_font={"color": INK_SECONDARY}
    )
    fig.update_yaxes(
        gridcolor=GRIDLINE, linecolor=BASELINE, tickfont={"color": INK_MUTED}, title_font={"color": INK_SECONDARY}
    )
    return fig


def inject_page_css() -> str:
    """One shared stylesheet: type scale, spacing, card surfaces, sidebar,
    inputs, tables and the stat-tile treatment for st.metric() -- so the KPI
    row, every chart card, and the sidebar nav all read as one design system
    across pages rather than un-styled Streamlit defaults."""
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT_FAMILY};
    }}

    /* ---- page plane & default Streamlit chrome cleanup ---- */
    .stApp {{
        background-color: {PAGE_PLANE};
    }}
    #MainMenu, footer, header[data-testid="stHeader"] {{
        background: transparent;
    }}
    div.block-container {{
        padding-top: 1.6rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }}

    /* ---- typography scale ---- */
    h1 {{
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        color: {INK_PRIMARY} !important;
    }}
    h2, h3 {{
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        color: {INK_PRIMARY} !important;
    }}
    p, li, .stMarkdown {{
        color: {INK_SECONDARY};
    }}
    [data-testid="stCaptionContainer"] {{
        color: {INK_MUTED} !important;
    }}

    /* ---- section header component (see page_header/section_header) ---- */
    .sq-page-header {{
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding-bottom: 14px;
        margin-bottom: 18px;
        border-bottom: 1px solid {GRIDLINE};
    }}
    .sq-page-header .sq-icon {{
        font-size: 30px;
        line-height: 1;
        margin-top: 2px;
    }}
    .sq-page-header .sq-title {{
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: {INK_PRIMARY};
        margin: 0;
    }}
    .sq-page-header .sq-subtitle {{
        font-size: 0.95rem;
        color: {INK_MUTED};
        margin-top: 4px;
        max-width: 92ch;
    }}
    .sq-section {{
        display: flex;
        align-items: center;
        gap: 9px;
        margin: 30px 0 12px 0;
    }}
    .sq-section .sq-section-icon {{
        font-size: 1.15rem;
    }}
    .sq-section .sq-section-title {{
        font-size: 1.18rem;
        font-weight: 700;
        color: {INK_PRIMARY};
        letter-spacing: -0.01em;
    }}
    .sq-section .sq-section-rule {{
        flex: 1;
        height: 1px;
        background: {GRIDLINE};
    }}
    .sq-eyebrow {{
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {ACCENT};
        background: {ACCENT_SOFT};
        border: 1px solid {ACCENT_SOFT_BORDER};
        border-radius: 999px;
        padding: 3px 10px;
        margin-bottom: 10px;
    }}

    /* ---- card surfaces: st.metric + bordered st.container ---- */
    [data-testid="stMetric"] {{
        background-color: {CHART_SURFACE};
        border: 1px solid {GRIDLINE};
        border-radius: 12px;
        padding: 16px 18px 12px 18px;
        box-shadow: 0 1px 2px rgba(11,11,11,0.03);
        transition: border-color 0.15s ease;
    }}
    [data-testid="stMetric"]:hover {{
        border-color: {ACCENT_SOFT_BORDER};
    }}
    [data-testid="stMetricLabel"] {{
        color: {INK_SECONDARY} !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {INK_PRIMARY} !important;
        font-variant-numeric: normal;
        font-weight: 700 !important;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CHART_SURFACE};
        border-radius: 14px !important;
        border-color: {GRIDLINE} !important;
        box-shadow: 0 1px 3px rgba(11,11,11,0.04);
    }}
    [data-testid="stVerticalBlockBorderWrapper"] > div {{
        border-radius: 14px;
    }}

    /* ---- status badges ---- */
    .status-badge {{
        display: inline-block;
        border-radius: 999px;
        padding: 1px 9px;
        font-size: 0.85em;
        font-weight: 600;
        margin-right: 6px;
    }}

    /* ---- sidebar ---- */
    section[data-testid="stSidebar"] {{
        background-color: #ffffff;
        border-right: 1px solid {GRIDLINE};
    }}
    section[data-testid="stSidebar"] .sq-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 4px 16px 4px;
        margin-bottom: 8px;
        border-bottom: 1px solid {GRIDLINE};
    }}
    section[data-testid="stSidebar"] .sq-brand .sq-brand-mark {{
        font-size: 22px;
    }}
    section[data-testid="stSidebar"] .sq-brand .sq-brand-name {{
        font-weight: 800;
        font-size: 1.05rem;
        color: {INK_PRIMARY};
        letter-spacing: -0.01em;
    }}
    section[data-testid="stSidebar"] .sq-brand .sq-brand-tag {{
        font-size: 0.7rem;
        color: {INK_MUTED};
        font-weight: 500;
    }}

    /* ---- inputs & buttons ---- */
    .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {{
        border-radius: 9px !important;
    }}
    .stTextInput input:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 1px {ACCENT} !important;
    }}
    .stButton > button, .stDownloadButton > button {{
        border-radius: 9px !important;
        font-weight: 600 !important;
        border: 1px solid {GRIDLINE} !important;
    }}
    .stButton > button[kind="primary"] {{
        background-color: {ACCENT} !important;
        border-color: {ACCENT} !important;
    }}
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background-color: {ACCENT} !important;
    }}

    /* ---- tables ---- */
    [data-testid="stDataFrame"] {{
        border: 1px solid {GRIDLINE};
        border-radius: 10px;
        overflow: hidden;
    }}

    /* ---- tabs ---- */
    button[data-baseweb="tab"] {{
        font-weight: 600 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {ACCENT} !important;
    }}
    div[data-baseweb="tab-highlight"] {{
        background-color: {ACCENT} !important;
    }}
    </style>
    """


def page_header(title: str, subtitle: str = "", icon: str = "\U0001f6e1️", eyebrow: str = "") -> None:
    """Renders the shared page header (icon + title + one-line subtitle),
    replacing bare `st.title()` so every page opens with the same rhythm.
    Import and call once at the top of a page, after `inject_page_css()`."""
    import streamlit as st

    eyebrow_html = f'<div class="sq-eyebrow">{eyebrow}</div>' if eyebrow else ""
    subtitle_html = f'<div class="sq-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="sq-page-header">
            <div class="sq-icon">{icon}</div>
            <div>
                {eyebrow_html}
                <div class="sq-title">{title}</div>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, icon: str = "") -> None:
    """Replaces `st.subheader()` with an icon + title + trailing hairline
    rule, so every section break in the app looks identical."""
    import streamlit as st

    icon_html = f'<span class="sq-section-icon">{icon}</span>' if icon else ""
    st.markdown(
        f"""
        <div class="sq-section">
            {icon_html}
            <span class="sq-section-title">{title}</span>
            <span class="sq-section-rule"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand() -> None:
    """Renders the sidebar brand mark once per page, above the auto-generated
    page nav, so the sidebar reads as a designed nav rather than a bare list
    of filenames."""
    import streamlit as st

    st.sidebar.markdown(
        """
        <div class="sq-brand">
            <div class="sq-brand-mark">\U0001f6e1️</div>
            <div>
                <div class="sq-brand-name">StochastiQ</div>
                <div class="sq-brand-tag">Cyber risk quantification</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
