"""JobIntel's shared Streamlit styling and display components."""

from __future__ import annotations

from html import escape
from typing import Literal

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

PRIMARY = "#4F46E5"
NAVY = "#0F172A"
CANVAS = "#F8FAFC"
CARD = "#FFFFFF"
BORDER = "#E2E8F0"
MUTED = "#64748B"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"

TagKind = Literal["skill", "work_mode", "matched", "missing", "status"]


def apply_theme() -> None:
    """Inject the shared styling once per page run.

    Streamlit creates its own DOM, so CSS is kept here to make the visual system
    consistent without duplicating style decisions in every page.
    """
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"] {{
            font-family: 'Inter', sans-serif;
        }}

        [data-testid="stAppViewContainer"] {{
            background: {CANVAS};
            color: {NAVY};
        }}

        [data-testid="stHeader"] {{
            background: rgba(248, 250, 252, 0.92);
            border-bottom: 1px solid {BORDER};
        }}

        [data-testid="stSidebar"] {{
            background: {NAVY};
            border-right: 1px solid #1E293B;
            min-width: 260px;
        }}

        [data-testid="stSidebar"] * {{ color: #E2E8F0; }}
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ padding-top: 0.5rem; }}
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
            border-radius: 8px;
            color: #94A3B8;
            margin: 0.15rem 0.5rem;
            padding: 0.65rem 0.75rem;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
            background: #1E293B;
            color: #FFFFFF;
        }}
        [data-testid="stSidebar"] [aria-current="page"] {{
            background: {PRIMARY} !important;
            color: #FFFFFF !important;
            font-weight: 600;
        }}

        .block-container {{ max-width: 1600px; padding-top: 2rem; padding-bottom: 2rem; }}
        h1, h2, h3 {{ color: {NAVY}; letter-spacing: -0.02em; }}
        h1 {{ font-weight: 700; }}
        p, span, td, th, [data-testid="stMetricValue"] {{
            font-variant-numeric: tabular-nums lining-nums;
        }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 16px;
            box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04),
                        0 1px 2px -1px rgba(15, 23, 42, 0.02);
        }}

        .jobintel-kpi {{
            background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px;
            box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04);
            min-height: 150px; padding: 1.25rem; box-sizing: border-box;
        }}
        .jobintel-kpi-label {{
            color: {MUTED}; font-size: 0.72rem; font-weight: 600;
            letter-spacing: .06em; text-transform: uppercase;
        }}
        .jobintel-kpi-value {{
            color: {NAVY}; font-size: 1.75rem; font-weight: 700;
            letter-spacing: -.02em; line-height: 1.25; margin: .55rem 0 .4rem;
        }}
        .jobintel-kpi-detail {{ color: {MUTED}; font-size: .8rem; }}
        .jobintel-tag {{
            display: inline-block; border-radius: 9999px; font-size: .72rem;
            font-weight: 600; line-height: 1; margin: 0 .25rem .25rem 0;
            padding: .42rem .6rem;
        }}
        .jobintel-skill {{ background: #F1F5F9; color: #334155; }}
        .jobintel-work-mode {{ background: #EFF6FF; color: #1D4ED8; }}
        .jobintel-matched {{ background: #DCFCE7; color: #166534; }}
        .jobintel-missing {{ background: #FEE2E2; color: #B91C1C; }}
        .jobintel-status {{ background: #ECFDF5; color: #047857; }}
        .jobintel-score {{
            align-items: center; background: conic-gradient(var(--score-color) var(--score), #E2E8F0 0);
            border-radius: 50%; display: flex; height: 92px; justify-content: center; width: 92px;
        }}
        .jobintel-score::before {{
            background: {CARD}; border-radius: 50%; content: ''; height: 74px; position: absolute; width: 74px;
        }}
        .jobintel-score-value {{ color: {NAVY}; font-size: 1.1rem; font-weight: 700; position: relative; }}
        .jobintel-page-kicker {{
            color: {MUTED}; font-size: .85rem; margin-top: -.6rem; margin-bottom: 1.25rem;
        }}
        .jobintel-empty {{
            background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 16px;
            color: {MUTED}; padding: 2rem; text-align: center;
        }}
        .jobintel-empty h3 {{ color: {NAVY}; font-size: 1rem; margin: 0 0 .45rem; }}
        .jobintel-empty p {{ margin: 0; }}
        .jobintel-sidebar-brand {{ border-bottom: 1px solid #1E293B; padding: 0.5rem 0 1.15rem; }}
        .jobintel-sidebar-logo {{ color: #FFFFFF; font-size: 1.25rem; font-weight: 700; letter-spacing: -.02em; }}
        .jobintel-live {{
            background: {PRIMARY}; border-radius: 999px; color: #FFFFFF; font-size: .63rem;
            font-weight: 700; letter-spacing: .08em; margin-left: .4rem; padding: .22rem .45rem;
        }}
        .stButton > button, [data-testid="stDownloadButton"] > button {{
            border: 1px solid {BORDER}; border-radius: 8px; color: {NAVY}; font-weight: 500;
        }}
        .stButton > button[kind="primary"] {{ background: {PRIMARY}; border-color: {PRIMARY}; color: #FFFFFF; }}
        [data-testid="stSelectbox"] > div > div, [data-testid="stTextInput"] input,
        [data-testid="stFileUploader"] section {{ border-radius: 8px; }}
        @media (max-width: 768px) {{
            .block-container {{ padding: 1rem; }}
            .jobintel-kpi {{ min-height: 128px; padding: 1rem; }}
            .jobintel-kpi-value {{ font-size: 1.4rem; }}
            [data-testid="stSidebar"] {{ min-width: 0; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Render the stable branding above Streamlit's navigation."""
    st.sidebar.markdown(
        """
        <div class="jobintel-sidebar-brand">
          <span class="jobintel-sidebar-logo">JobIntel</span>
          <span class="jobintel-live">LIVE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("India job-market intelligence")


def page_header(title: str, subtitle: str) -> None:
    """Render a consistent page title and concise context line."""
    st.title(title)
    st.markdown(f'<p class="jobintel-page-kicker">{escape(subtitle)}</p>', unsafe_allow_html=True)


def kpi_card(label: str, value: str = "—", detail: str = "") -> None:
    """Render a compact KPI card without inventing data values."""
    st.markdown(
        f"""
        <div class="jobintel-kpi">
          <div class="jobintel-kpi-label">{escape(label)}</div>
          <div class="jobintel-kpi-value">{escape(value)}</div>
          <div class="jobintel-kpi-detail">{escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tag(label: str, kind: TagKind = "skill") -> str:
    """Return safe HTML for a small, consistently coloured category tag."""
    tag_class = {
        "skill": "jobintel-skill",
        "work_mode": "jobintel-work-mode",
        "matched": "jobintel-matched",
        "missing": "jobintel-missing",
        "status": "jobintel-status",
    }[kind]
    return f'<span class="jobintel-tag {tag_class}">{escape(label)}</span>'


def score_ring(score: float | None) -> None:
    """Render an HTML/CSS score ring for resume-match results."""
    if score is None:
        score_value, score_percent, color = "—", 0.0, BORDER
    else:
        bounded = max(0.0, min(score, 100.0))
        score_value, score_percent = f"{bounded:.0f}%", bounded
        color = SUCCESS if bounded >= 75 else WARNING if bounded >= 50 else DANGER
    st.markdown(
        f"""
        <div class="jobintel-score" style="--score: {score_percent}%; --score-color: {color};">
          <span class="jobintel-score-value">{score_value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_card(title: str, subtitle: str | None = None) -> DeltaGenerator:
    """Create a bordered content card and return it for page-specific content."""
    card = st.container(border=True)
    card.subheader(title)
    if subtitle:
        card.caption(subtitle)
    return card


def empty_state(title: str, message: str) -> None:
    """Render a consistent, readable no-data or no-result state."""
    st.markdown(
        f"""
        <div class="jobintel-empty">
          <h3>{escape(title)}</h3>
          <p>{escape(message)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
