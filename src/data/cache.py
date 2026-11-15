"""Streamlit-aware cached queries for the JobIntel interface."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.data.database import DATABASE_PATH, fetch_jobs


@st.cache_data(show_spinner=False)
def load_jobs_cached(database_path: str = str(DATABASE_PATH)) -> pd.DataFrame:
    """Read SQLite once per input path until a collection action clears the cache."""
    return fetch_jobs(Path(database_path))


def clear_job_cache() -> None:
    """Clear job-query results after data collection changes the database."""
    load_jobs_cached.clear()
