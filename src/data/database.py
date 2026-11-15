"""SQLite storage and query functions for JobIntel job postings."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "jobintel.db"

JOB_COLUMNS = [
    "source_id",
    "source",
    "source_type",
    "title",
    "company",
    "city",
    "work_mode",
    "salary_min_lpa",
    "salary_max_lpa",
    "experience_band",
    "skills",
    "description",
    "posted_date",
    "collected_at",
]


def get_connection(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open the local database, creating its parent directory when needed."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Create the jobs table and indexes used by collection and analytics."""
    with get_connection(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                city TEXT,
                work_mode TEXT,
                salary_min_lpa REAL,
                salary_max_lpa REAL,
                experience_band TEXT,
                skills TEXT NOT NULL DEFAULT '[]',
                description TEXT,
                posted_date TEXT,
                collected_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);
            CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city);
            CREATE INDEX IF NOT EXISTS idx_jobs_source_type ON jobs(source_type);
            """
        )


def _as_text(value: Any, default: str = "") -> str:
    """Turn pandas empty values into database-safe text."""
    if value is None or pd.isna(value):
        return default
    return str(value).strip()


def _as_number(value: Any) -> float | None:
    """Convert a value to a finite float, leaving unavailable values as NULL."""
    number = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(number) else float(number)


def _as_skill_json(value: Any) -> str:
    """Store skills as JSON so later NLP stages can read a stable list format."""
    if isinstance(value, list):
        skills = [str(skill).strip() for skill in value if str(skill).strip()]
    elif value is None or pd.isna(value):
        skills = []
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            skills = []
        else:
            try:
                decoded = json.loads(text)
                skills = decoded if isinstance(decoded, list) else [text]
            except json.JSONDecodeError:
                skills = [item.strip() for item in text.replace("|", ",").split(",") if item.strip()]
    else:
        skills = [str(value).strip()]
    return json.dumps(skills)


def _as_date(value: Any) -> str | None:
    """Convert dates to ISO dates so SQLite can sort them predictably."""
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.date().isoformat()


def _fallback_source_id(record: dict[str, Any]) -> str:
    """Create a repeatable identifier when a CSV does not provide one."""
    identity = "|".join(
        _as_text(record.get(field)) for field in ("title", "company", "city", "posted_date")
    )
    return f"csv-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"


def _job_values(record: dict[str, Any]) -> tuple[Any, ...]:
    """Normalise one imported record to the database schema."""
    source_id = _as_text(record.get("source_id")) or _fallback_source_id(record)
    return (
        source_id,
        _as_text(record.get("source"), "CSV import"),
        _as_text(record.get("source_type"), "csv"),
        _as_text(record.get("title"), "Untitled role"),
        _as_text(record.get("company")),
        _as_text(record.get("city")),
        _as_text(record.get("work_mode"), "Unspecified"),
        _as_number(record.get("salary_min_lpa")),
        _as_number(record.get("salary_max_lpa")),
        _as_text(record.get("experience_band"), "Unspecified"),
        _as_skill_json(record.get("skills")),
        _as_text(record.get("description")),
        _as_date(record.get("posted_date")),
        datetime.now(UTC).isoformat(),
    )


def upsert_jobs(jobs: pd.DataFrame, database_path: Path = DATABASE_PATH) -> int:
    """Insert or update jobs by source ID and return the number processed."""
    if jobs.empty:
        return 0

    initialize_database(database_path)
    values = [_job_values(record) for record in jobs.to_dict(orient="records")]
    placeholders = ", ".join("?" for _ in JOB_COLUMNS)
    updates = ", ".join(f"{column} = excluded.{column}" for column in JOB_COLUMNS[1:])
    statement = (
        f"INSERT INTO jobs ({', '.join(JOB_COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(source_id) DO UPDATE SET {updates}"
    )
    with get_connection(database_path) as connection:
        connection.executemany(statement, values)
    return len(values)


def fetch_jobs(database_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """Return all saved jobs with skills decoded from their JSON storage format."""
    initialize_database(database_path)
    with get_connection(database_path) as connection:
        jobs = pd.read_sql_query("SELECT * FROM jobs ORDER BY posted_date DESC, id DESC", connection)
    if jobs.empty:
        return jobs
    jobs["skills"] = jobs["skills"].map(json.loads)
    return jobs


def database_summary(database_path: Path = DATABASE_PATH) -> dict[str, int]:
    """Return small, truthful source counts for status badges and empty states."""
    initialize_database(database_path)
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT source_type, COUNT(*) AS count FROM jobs GROUP BY source_type"
        ).fetchall()
    return {str(row["source_type"]): int(row["count"]) for row in rows}


def delete_jobs_by_source_type(source_type: str, database_path: Path = DATABASE_PATH) -> int:
    """Delete one explicit source category, used only for removable demo records."""
    initialize_database(database_path)
    with get_connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM jobs WHERE source_type = ?", (source_type,))
    return max(cursor.rowcount, 0)
