"""Tests for SQLite job persistence."""

from __future__ import annotations

from pathlib import Path

from src.data.database import database_summary, delete_jobs_by_source_type, fetch_jobs, upsert_jobs


def test_upsert_round_trip_preserves_skills(sample_jobs, tmp_path: Path) -> None:
    """Jobs should survive SQLite storage with skills restored as a list."""
    database_path = tmp_path / "jobs.db"

    assert upsert_jobs(sample_jobs, database_path) == 2
    stored = fetch_jobs(database_path)

    assert len(stored) == 2
    assert stored.iloc[0]["skills"] == ["Python", "SQL", "PyTorch"]
    assert database_summary(database_path) == {"csv": 2}


def test_upsert_replaces_an_existing_source_record(sample_jobs, tmp_path: Path) -> None:
    """The source identifier prevents repeated imports from duplicating jobs."""
    database_path = tmp_path / "jobs.db"
    upsert_jobs(sample_jobs, database_path)
    updated = sample_jobs.copy()
    updated.loc[0, "company"] = "Updated Example"

    upsert_jobs(updated, database_path)
    stored = fetch_jobs(database_path)

    assert len(stored) == 2
    assert stored.loc[stored["source_id"] == "test-1", "company"].item() == "Updated Example"


def test_delete_jobs_by_source_type_only_removes_requested_source(sample_jobs, tmp_path: Path) -> None:
    """Removing demo rows must not remove a user's separate imported records."""
    database_path = tmp_path / "jobs.db"
    mixed = sample_jobs.copy()
    mixed.loc[0, "source_type"] = "sample"
    upsert_jobs(mixed, database_path)

    assert delete_jobs_by_source_type("sample", database_path) == 1
    assert len(fetch_jobs(database_path)) == 1
