"""Truthful, reusable aggregates for the JobIntel dashboard."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DashboardMetrics:
    """Values shown in the dashboard KPI row."""

    total_jobs: int
    average_salary_lpa: float | None
    top_city: str | None
    top_city_count: int
    top_skill: str | None
    top_skill_count: int


def apply_job_filters(
    jobs: pd.DataFrame,
    role: str = "All roles",
    city: str = "All cities",
    experience: str = "All experience levels",
    date_window: str = "All available dates",
) -> pd.DataFrame:
    """Return jobs matching the four visible dashboard filters."""
    filtered = jobs.copy()
    if role != "All roles":
        filtered = filtered[filtered["title"] == role]
    if city != "All cities":
        filtered = filtered[filtered["city"] == city]
    if experience != "All experience levels":
        filtered = filtered[filtered["experience_band"] == experience]

    days_by_window = {"Last 30 days": 30, "Last 90 days": 90, "Last 180 days": 180}
    if date_window in days_by_window:
        posted_dates = pd.to_datetime(filtered["posted_date"], errors="coerce", utc=True)
        latest_date = posted_dates.max()
        if pd.notna(latest_date):
            filtered = filtered.loc[posted_dates >= latest_date - pd.Timedelta(days=days_by_window[date_window])]
    return filtered.reset_index(drop=True)


def skill_counts(jobs: pd.DataFrame) -> pd.DataFrame:
    """Count CSV-provided or extracted skills once per matching job."""
    if jobs.empty or "skills" not in jobs:
        return pd.DataFrame(columns=["skill", "count"])
    skills = jobs[["id", "skills"]].explode("skills").dropna(subset=["skills"])
    skills["skill"] = skills["skills"].astype(str).str.strip()
    skills = skills[skills["skill"] != ""]
    return (
        skills.groupby("skill", as_index=False)["id"]
        .nunique()
        .rename(columns={"id": "count"})
        .sort_values(["count", "skill"], ascending=[False, True])
        .reset_index(drop=True)
    )


def calculate_metrics(jobs: pd.DataFrame) -> DashboardMetrics:
    """Calculate KPIs while retaining unavailable salary data as missing."""
    if jobs.empty:
        return DashboardMetrics(0, None, None, 0, None, 0)
    salaries = jobs[["salary_min_lpa", "salary_max_lpa"]].apply(pd.to_numeric, errors="coerce")
    salary_midpoints = salaries.mean(axis=1, skipna=True).dropna()
    cities = jobs["city"].replace("", pd.NA).dropna().value_counts()
    skills = skill_counts(jobs)
    return DashboardMetrics(
        total_jobs=len(jobs),
        average_salary_lpa=float(salary_midpoints.mean()) if not salary_midpoints.empty else None,
        top_city=str(cities.index[0]) if not cities.empty else None,
        top_city_count=int(cities.iloc[0]) if not cities.empty else 0,
        top_skill=str(skills.iloc[0]["skill"]) if not skills.empty else None,
        top_skill_count=int(skills.iloc[0]["count"]) if not skills.empty else 0,
    )


def city_counts(jobs: pd.DataFrame) -> pd.DataFrame:
    """Return real job-posting counts by non-empty city."""
    if jobs.empty:
        return pd.DataFrame(columns=["city", "count"])
    return jobs["city"].replace("", pd.NA).dropna().value_counts().rename_axis("city").reset_index(name="count")


def salary_by_experience(jobs: pd.DataFrame) -> pd.DataFrame:
    """Calculate 25th, median, and 90th salary percentiles by experience band."""
    if jobs.empty:
        return pd.DataFrame(columns=["experience_band", "p25", "median", "p90"])
    salary_data = jobs[["experience_band", "salary_min_lpa", "salary_max_lpa"]].copy()
    salary_data["midpoint"] = salary_data[["salary_min_lpa", "salary_max_lpa"]].apply(
        pd.to_numeric, errors="coerce"
    ).mean(axis=1, skipna=True)
    salary_data = salary_data.dropna(subset=["midpoint"])
    if salary_data.empty:
        return pd.DataFrame(columns=["experience_band", "p25", "median", "p90"])
    return (
        salary_data.groupby("experience_band", as_index=False)["midpoint"]
        .agg(p25=lambda values: values.quantile(0.25), median="median", p90=lambda values: values.quantile(0.90))
        .sort_values("median")
        .reset_index(drop=True)
    )


def skill_trend(jobs: pd.DataFrame, skill_limit: int = 5) -> pd.DataFrame:
    """Count common skills by available month without filling in fictional months."""
    if jobs.empty:
        return pd.DataFrame(columns=["month", "skill", "count"])
    dated = jobs.copy()
    dated["posted_date"] = pd.to_datetime(dated["posted_date"], errors="coerce", utc=True)
    dated = dated.dropna(subset=["posted_date"])
    if dated.empty:
        return pd.DataFrame(columns=["month", "skill", "count"])
    top_skills = skill_counts(dated).head(skill_limit)["skill"].tolist()
    trend = dated[["id", "posted_date", "skills"]].explode("skills")
    trend["skills"] = trend["skills"].astype(str).str.strip()
    trend = trend[trend["skills"].isin(top_skills)]
    trend["month"] = trend["posted_date"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    return (
        trend.groupby(["month", "skills"], as_index=False)["id"]
        .nunique()
        .rename(columns={"skills": "skill", "id": "count"})
        .sort_values(["month", "skill"])
    )


def jobs_for_skill(jobs: pd.DataFrame, skill: str) -> pd.DataFrame:
    """Return jobs that mention a selected skill, ignoring letter case."""
    needle = skill.strip().casefold()
    if jobs.empty or not needle:
        return jobs.iloc[0:0].copy()
    matching = jobs["skills"].map(
        lambda skills: any(str(item).strip().casefold() == needle for item in skills)
    )
    return jobs.loc[matching].copy()


def skill_growth_percent(jobs: pd.DataFrame, skill: str) -> float | None:
    """Compare the two latest observed months for a skill when both are usable."""
    matching = jobs_for_skill(jobs, skill).copy()
    matching["posted_date"] = pd.to_datetime(matching["posted_date"], errors="coerce", utc=True)
    matching = matching.dropna(subset=["posted_date"])
    if matching.empty:
        return None
    month_counts = matching.groupby(
        matching["posted_date"].dt.tz_localize(None).dt.to_period("M")
    ).size().sort_index()
    if len(month_counts) < 2 or month_counts.iloc[-2] == 0:
        return None
    return float((month_counts.iloc[-1] - month_counts.iloc[-2]) / month_counts.iloc[-2] * 100)


def co_occurring_skills(jobs: pd.DataFrame, skill: str, limit: int = 8) -> pd.DataFrame:
    """Find skills sharing job postings and their observed salary difference.

    Salary impact means the pair's average listed salary minus the selected
    skill's average listed salary. It is descriptive rather than causal.
    """
    matching = jobs_for_skill(jobs, skill)
    if matching.empty:
        return pd.DataFrame(columns=["skill", "job_count", "pair_share", "salary_impact_lpa"])

    base_salary = matching[["salary_min_lpa", "salary_max_lpa"]].apply(pd.to_numeric, errors="coerce").mean(axis=1).mean()
    rows: list[dict[str, float | int | str | None]] = []
    selected = skill.casefold()
    for candidate in skill_counts(matching)["skill"]:
        if candidate.casefold() == selected:
            continue
        pair_jobs = jobs_for_skill(matching, candidate)
        pair_salary = pair_jobs[["salary_min_lpa", "salary_max_lpa"]].apply(
            pd.to_numeric, errors="coerce"
        ).mean(axis=1).mean()
        rows.append(
            {
                "skill": candidate,
                "job_count": len(pair_jobs),
                "pair_share": len(pair_jobs) / len(matching) * 100,
                "salary_impact_lpa": None if pd.isna(base_salary) or pd.isna(pair_salary) else float(pair_salary - base_salary),
            }
        )
    return pd.DataFrame(rows).sort_values(["job_count", "skill"], ascending=[False, True]).head(limit).reset_index(drop=True) if rows else pd.DataFrame(columns=["skill", "job_count", "pair_share", "salary_impact_lpa"])


def roles_for_skill(jobs: pd.DataFrame, skill: str) -> pd.DataFrame:
    """Summarise roles that hire for a selected skill from matching postings."""
    matching = jobs_for_skill(jobs, skill).copy()
    if matching.empty:
        return pd.DataFrame(columns=["role", "postings", "average_salary_lpa", "top_city"])
    matching["salary_midpoint"] = matching[["salary_min_lpa", "salary_max_lpa"]].apply(
        pd.to_numeric, errors="coerce"
    ).mean(axis=1)
    rows: list[dict[str, str | int | float | None]] = []
    for role, group in matching.groupby("title"):
        cities = group["city"].replace("", pd.NA).dropna().value_counts()
        salary = group["salary_midpoint"].mean()
        rows.append(
            {
                "role": role,
                "postings": len(group),
                "average_salary_lpa": None if pd.isna(salary) else float(salary),
                "top_city": str(cities.index[0]) if not cities.empty else "Not listed",
            }
        )
    return pd.DataFrame(rows).sort_values(["postings", "role"], ascending=[False, True]).reset_index(drop=True)
