"""Accurate project information drawn from the local JobIntel database."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.cache import clear_job_cache, load_jobs_cached
from src.data.database import database_summary
from src.ui.theme import empty_state, kpi_card, page_header, section_card, tag


def source_label(summary: dict[str, int]) -> str:
    """Describe only the source categories currently stored in SQLite."""
    labels = {
        "api": "Adzuna API",
        "csv": "CSV import",
        "sample": "Demo CSV",
    }
    present = [labels.get(source_type, source_type) for source_type in summary]
    return ", ".join(present) if present else "No source imported"


page_header("About JobIntel", "A transparent portfolio project for exploring India’s data and AI job market.")

summary = database_summary()
with st.spinner("Reading local project status..."):
    jobs = load_jobs_cached()

status_column, refresh_column = st.columns([4, 1])
with status_column:
    if summary.get("sample", 0):
        st.markdown(tag("Sample data", "status"), unsafe_allow_html=True)
        st.caption("The database contains demo CSV records. They are for application testing, not market claims.")
    elif not jobs.empty:
        st.markdown(tag("Database loaded", "status"), unsafe_allow_html=True)
with refresh_column:
    if st.button("Refresh data", use_container_width=True):
        clear_job_cache()
        st.rerun()

if jobs.empty:
    empty_state(
        "Project database is empty",
        "Run python scripts/import_jobs.py --source csv in PowerShell to load the included demo data.",
    )
    st.stop()

latest_posted = pd.to_datetime(jobs["posted_date"], errors="coerce").max()
kpis = st.columns(3)
with kpis[0]:
    kpi_card("Local postings", f"{len(jobs):,}", "Records currently stored in SQLite")
with kpis[1]:
    kpi_card("Current sources", str(len(summary)), source_label(summary))
with kpis[2]:
    kpi_card("Latest posting date", latest_posted.date().isoformat() if pd.notna(latest_posted) else "—", "Based on imported source data")

mission = section_card("What JobIntel does")
with mission:
    st.write(
        "JobIntel imports job postings into a local SQLite database, lets you explore the imported fields in Streamlit, "
        "and compares an uploaded resume against the local postings. It is designed as a portfolio project and does not "
        "claim to represent the whole Indian job market."
    )

pipeline = section_card("How the current pipeline works")
with pipeline:
    st.markdown(
        "1. **Import** — `scripts/import_jobs.py` loads the Adzuna API when configured, or a job-postings CSV.\n"
        "2. **Store** — records are inserted or updated in `data/jobintel.db`.\n"
        "3. **Explore** — Dashboard and Skills Explorer calculate their displays from those records and state when they use sample data.\n"
        "4. **Match** — the Resume Matcher reads PDF/DOCX text in memory, extracts curated skills with spaCy, and ranks local jobs with `all-MiniLM-L6-v2`."
    )

privacy = section_card("Resume handling")
with privacy:
    st.write(
        "Resume files are read in memory during the active Streamlit session. The app does not write uploaded resume files or their text to SQLite or the project folder. "
        "The session retains only derived skills and job-match results so it can display the analysis."
    )

faq = section_card("FAQ")
with faq:
    with st.expander("Which job sources can this project use?"):
        st.write("The included importer supports the Adzuna public API and user-provided CSV files. It does not scrape job boards.")
    with st.expander("How is the resume match score calculated?"):
        st.write("The score blends 70% sentence-embedding similarity and 30% curated skill coverage. It ranks the imported jobs; it is not a hiring prediction.")
    with st.expander("Why can a chart be empty?"):
        st.write("A chart stays empty when the imported records do not contain the fields it needs. For example, a trend needs postings from at least two months.")
    with st.expander("Where are credentials stored?"):
        st.write("Optional Adzuna credentials belong in a local .env file. That file is excluded from Git.")
