"""Application entry point for the JobIntel Streamlit workspace."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.theme import apply_theme, render_sidebar_brand


st.set_page_config(
    page_title="JobIntel | Job Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar_brand()

pages = {
    "Explore": [
        st.Page("pages/data_manager.py", title="Data Manager", icon="🗃️"),
        # Page paths are relative to this entry point, not the project root.
        st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("pages/skills_explorer.py", title="Skills Explorer", icon="🧠"),
    ],
    "Match": [
        st.Page("pages/resume_matcher.py", title="Resume Matcher", icon="📄"),
        st.Page("pages/job_search.py", title="Job Search Assistant", icon="🔎"),
    ],
    "Project": [
        st.Page("pages/about.py", title="About", icon="ℹ️"),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
