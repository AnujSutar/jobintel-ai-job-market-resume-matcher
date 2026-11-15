"""CSV and API-source loading helpers for JobIntel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data.database import DATABASE_PATH, upsert_jobs


class DataLoadError(ValueError):
    """Raised when an input dataset cannot produce usable job records."""


@dataclass(frozen=True)
class ImportResult:
    """A short result that the command line and UI can report to the user."""

    source: str
    records_processed: int
    database_path: Path


def _prepare_dataframe(jobs: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Normalise a raw CSV dataframe into fields accepted by SQLite storage."""
    if jobs.empty:
        raise DataLoadError("The CSV contains no job records.")

    jobs = jobs.rename(columns={key: value for key, value in CSV_COLUMN_ALIASES.items() if key in jobs}).copy()
    if "title" not in jobs.columns:
        raise DataLoadError("The CSV needs a 'title' or 'job_title' column.")

    defaults = {
        "source": "Demo CSV" if source_name == "sample_jobs.csv" else "CSV import",
        "source_type": "sample" if source_name == "sample_jobs.csv" else "csv",
        "company": "",
        "city": "",
        "work_mode": "Unspecified",
        "salary_min_lpa": None,
        "salary_max_lpa": None,
        "experience_band": "Unspecified",
        "skills": "[]",
        "description": "",
        "posted_date": None,
    }
    for column, default in defaults.items():
        if column not in jobs.columns:
            jobs[column] = default
    if "source_id" not in jobs.columns:
        jobs["source_id"] = ""
    return jobs


CSV_COLUMN_ALIASES = {
    "job_title": "title",
    "position": "title",
    "company_name": "company",
    "employer": "company",
    "location": "city",
    "job_location": "city",
    "remote": "work_mode",
    "min_salary_lpa": "salary_min_lpa",
    "max_salary_lpa": "salary_max_lpa",
    "salary_min": "salary_min_lpa",
    "salary_max": "salary_max_lpa",
    "experience": "experience_band",
    "job_description": "description",
    "date_posted": "posted_date",
}


def prepare_csv_jobs(csv_path: Path) -> pd.DataFrame:
    """Read a CSV and map common job-dataset column names to JobIntel fields."""
    if not csv_path.exists():
        raise DataLoadError(f"CSV file was not found: {csv_path}")

    try:
        jobs = pd.read_csv(csv_path)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as error:
        raise DataLoadError(f"Could not read the CSV file: {error}") from error

    return _prepare_dataframe(jobs, csv_path.name)


def prepare_uploaded_csv(uploaded_file: object, filename: str) -> pd.DataFrame:
    """Read and normalise a Streamlit CSV upload without saving the raw file."""
    try:
        jobs = pd.read_csv(uploaded_file)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as error:
        raise DataLoadError(f"Could not read the uploaded CSV: {error}") from error
    return _prepare_dataframe(jobs, filename)


def quality_report(jobs: pd.DataFrame) -> dict[str, int]:
    """Return simple checks so users can verify a CSV before importing it."""
    duplicate_columns = ["title", "company", "city", "posted_date"]
    skill_values = jobs["skills"].map(lambda value: str(value).strip() not in {"", "[]", "nan", "None"})
    return {
        "rows": len(jobs),
        "missing_titles": int(jobs["title"].isna().sum() + jobs["title"].astype(str).str.strip().eq("").sum()),
        "duplicate_rows": int(jobs.duplicated(subset=duplicate_columns, keep=False).sum()),
        "rows_with_salary": int(jobs[["salary_min_lpa", "salary_max_lpa"]].notna().any(axis=1).sum()),
        "rows_with_skills": int(skill_values.sum()),
    }


def import_csv_jobs(
    csv_path: Path,
    database_path: Path = DATABASE_PATH,
) -> ImportResult:
    """Load a job CSV into SQLite and return a small import summary."""
    jobs = prepare_csv_jobs(csv_path)
    processed = upsert_jobs(jobs, database_path)
    return ImportResult("CSV fallback", processed, database_path)
