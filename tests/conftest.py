"""Shared fixtures for JobIntel's fast, offline test suite."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def sample_jobs() -> pd.DataFrame:
    """Provide a small job table with stable values for analytics tests."""
    return pd.DataFrame(
        [
            {
                "id": 1,
                "source_id": "test-1",
                "source": "Test CSV",
                "source_type": "csv",
                "title": "Data Scientist",
                "company": "Example A",
                "city": "Bengaluru",
                "work_mode": "Hybrid",
                "salary_min_lpa": 10.0,
                "salary_max_lpa": 14.0,
                "experience_band": "1-3 years",
                "skills": ["Python", "SQL", "PyTorch"],
                "description": "Python machine learning role",
                "posted_date": "2026-10-01",
            },
            {
                "id": 2,
                "source_id": "test-2",
                "source": "Test CSV",
                "source_type": "csv",
                "title": "Data Analyst",
                "company": "Example B",
                "city": "Pune",
                "work_mode": "Remote",
                "salary_min_lpa": 6.0,
                "salary_max_lpa": 8.0,
                "experience_band": "0-2 years",
                "skills": ["Python", "SQL", "Excel"],
                "description": "Python and SQL analytics role",
                "posted_date": "2026-09-01",
            },
        ]
    )
