"""Tests for safe platform links and recommendation guidance."""

from __future__ import annotations

from src.ml.job_search import build_search_query, improvement_plan, platform_search_urls


def test_search_urls_include_query_and_location() -> None:
    """Outbound platform URLs should reflect the chosen target without scraping."""
    query = build_search_query("Data Scientist", ["Python", "SQL"])
    urls = platform_search_urls(query, "Bengaluru")

    assert query == "Data Scientist Python SQL"
    assert set(urls) == {"LinkedIn Jobs", "Indeed India", "Naukri"}
    assert "linkedin.com/jobs/search" in urls["LinkedIn Jobs"]
    assert "Bengaluru" in urls["Indeed India"]


def test_improvement_plan_supplies_skill_specific_action() -> None:
    """Known skills should receive useful, concrete improvement guidance."""
    plan = improvement_plan([("SQL", 4), ("Unlisted skill", 2)])

    assert plan[0][0] == "SQL"
    assert "window functions" in plan[0][2]
    assert "portfolio project" in plan[1][2]
