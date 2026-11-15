"""CSV validation and import page for expanding JobIntel beyond demo data."""

from __future__ import annotations

import streamlit as st

from src.data.cache import clear_job_cache, load_jobs_cached
from src.data.database import database_summary, delete_jobs_by_source_type, upsert_jobs
from src.data.loaders import DataLoadError, prepare_uploaded_csv, quality_report
from src.ui.theme import empty_state, kpi_card, page_header, section_card


def prepare_upload() -> None:
    """Validate the uploaded CSV and retain only normalised data for import."""
    uploaded = st.session_state.get("jobs_csv_upload")
    if uploaded is None:
        return
    try:
        prepared = prepare_uploaded_csv(uploaded, uploaded.name)
    except DataLoadError as error:
        st.session_state.pop("prepared_jobs_upload", None)
        st.session_state.upload_error = str(error)
        return
    st.session_state.prepared_jobs_upload = prepared
    st.session_state.pop("upload_error", None)


page_header("Data Manager", "Validate and import a legal job-postings CSV to expand the roles, cities, and analysis in JobIntel.")

summary = database_summary()
with st.spinner("Loading local data status..."):
    current_jobs = load_jobs_cached()

summary_card = section_card("Current database")
with summary_card:
    columns = st.columns(3)
    with columns[0]:
        kpi_card("Stored postings", f"{len(current_jobs):,}", "Rows currently in SQLite")
    with columns[1]:
        kpi_card("Source types", str(len(summary)), ", ".join(summary) if summary else "No source yet")
    with columns[2]:
        if summary.get("sample", 0):
            kpi_card("Demo records", str(summary["sample"]), "Add your own CSV to broaden the data")
        else:
            kpi_card("Demo records", "0", "No sample records currently stored")

if summary.get("sample", 0):
    sample_card = section_card("Remove demo records", "Use this after importing your own data to keep sample rows out of your analysis.")
    with sample_card:
        confirmed = st.checkbox("I understand this will permanently remove only the demo CSV rows from local SQLite.")
        if st.button("Remove demo records", disabled=not confirmed):
            deleted = delete_jobs_by_source_type("sample")
            clear_job_cache()
            st.success(f"Removed {deleted:,} demo records. Choose Refresh data on the analytics pages.")

upload_card = section_card("Import a job-postings CSV", "The file is checked in memory before import. Importing adds or updates jobs by source ID; it does not delete existing records.")
with upload_card:
    st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="jobs_csv_upload",
        on_change=prepare_upload,
        help="Required: title or job_title. Useful optional fields: company, city/location, salaries, skills, description, posted_date.",
    )
    st.caption("Use a legal dataset such as a Kaggle download whose license permits your use. The original upload is not saved to the project folder.")

if st.session_state.get("upload_error"):
    st.error(st.session_state.upload_error)

prepared_jobs = st.session_state.get("prepared_jobs_upload")
if prepared_jobs is None:
    empty_state("Choose a CSV to validate it", "After you upload a file, JobIntel will show its quality checks and a preview before importing it.")
    st.stop()

report = quality_report(prepared_jobs)
quality_card = section_card("Import preview", "Review these checks before adding the rows to your local SQLite database.")
with quality_card:
    columns = st.columns(5)
    labels = [
        ("Rows", report["rows"]),
        ("Missing titles", report["missing_titles"]),
        ("Potential duplicates", report["duplicate_rows"]),
        ("Rows with salary", report["rows_with_salary"]),
        ("Rows with skills", report["rows_with_skills"]),
    ]
    for column, (label, value) in zip(columns, labels):
        with column:
            kpi_card(label, str(value))
    st.dataframe(prepared_jobs.head(20), hide_index=True, use_container_width=True)
    if report["missing_titles"]:
        st.warning("Rows without a title will be stored as ‘Untitled role’. Remove or correct them in your CSV for better analysis.")
    if st.button(f"Import {report['rows']:,} validated rows", type="primary"):
        with st.spinner("Importing validated jobs into SQLite..."):
            processed = upsert_jobs(prepared_jobs)
            clear_job_cache()
        st.success(f"Imported or updated {processed:,} job postings. Open Dashboard or Skills Explorer and choose Refresh data.")
