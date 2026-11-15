"""Tests for transparent dashboard and skills aggregates."""

from __future__ import annotations

from src.data.analytics import (
    apply_job_filters,
    calculate_metrics,
    co_occurring_skills,
    jobs_for_skill,
    salary_by_experience,
    skill_counts,
)


def test_metrics_and_skill_counts_are_calculated_from_input(sample_jobs) -> None:
    """KPI values and skill demand should come directly from job rows."""
    metrics = calculate_metrics(sample_jobs)
    skills = skill_counts(sample_jobs)

    assert metrics.total_jobs == 2
    assert metrics.average_salary_lpa == 9.5
    assert metrics.top_city == "Bengaluru"
    assert metrics.top_skill == "Python"
    assert skills.iloc[0].to_dict() == {"skill": "Python", "count": 2}


def test_filters_and_skill_co_occurrence(sample_jobs) -> None:
    """Filters narrow postings and pairs count only jobs containing both skills."""
    filtered = apply_job_filters(sample_jobs, role="Data Scientist")
    pairs = co_occurring_skills(sample_jobs, "Python")

    assert len(filtered) == 1
    assert len(jobs_for_skill(sample_jobs, "sql")) == 2
    assert pairs.loc[pairs["skill"] == "SQL", "job_count"].item() == 2
    assert len(salary_by_experience(sample_jobs)) == 2
