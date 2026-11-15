"""Tests for in-memory CSV validation used by the Data Manager."""

from __future__ import annotations

from io import StringIO

from src.data.loaders import prepare_uploaded_csv, quality_report


def test_uploaded_csv_maps_common_columns_and_reports_quality() -> None:
    """A user upload should work without writing its raw CSV to disk."""
    upload = StringIO(
        "job_title,company_name,location,skills\n"
        "AI Engineer,Example Labs,Hyderabad,Python|PyTorch\n"
        "AI Engineer,Example Labs,Hyderabad,Python|PyTorch\n"
    )

    jobs = prepare_uploaded_csv(upload, "new_jobs.csv")
    report = quality_report(jobs)

    assert jobs.loc[0, "title"] == "AI Engineer"
    assert jobs.loc[0, "company"] == "Example Labs"
    assert jobs.loc[0, "city"] == "Hyderabad"
    assert report == {
        "rows": 2,
        "missing_titles": 0,
        "duplicate_rows": 2,
        "rows_with_salary": 0,
        "rows_with_skills": 2,
    }
