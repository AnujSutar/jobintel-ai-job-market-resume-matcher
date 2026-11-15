"""Tests for curated skill extraction and deterministic job ranking."""

from __future__ import annotations

import numpy as np

from src.ml.matcher import rank_jobs, recommended_skills
from src.ml.skills import extract_skills, group_skills


class FakeEmbeddingModel:
    """A deterministic replacement that keeps unit tests offline and fast."""

    def encode(self, texts, **_kwargs):
        vectors = [np.array([1.0, 0.0])]
        vectors.extend(
            [np.array([1.0, 0.0]), np.array([0.0, 1.0])][: len(texts) - 1]
        )
        return np.vstack(vectors)


def test_skill_extraction_groups_aliases() -> None:
    """The curated matcher recognises aliases and assigns UI categories."""
    skills = extract_skills("Python, SQL, sklearn, AWS, and Docker")

    assert skills == ["Python", "SQL", "scikit-learn", "AWS", "Docker"]
    assert group_skills(skills)["ML & Data"] == ["scikit-learn"]


def test_rank_jobs_prefers_semantic_and_skill_overlap(sample_jobs) -> None:
    """A more similar job with stronger skill coverage should rank first."""
    matches = rank_jobs(
        "Python and SQL data science experience",
        ["Python", "SQL"],
        sample_jobs,
        model=FakeEmbeddingModel(),
    )

    assert matches[0].job_id == 1
    assert matches[0].matched_skills == ["Python", "SQL"]
    assert "PyTorch" in matches[0].missing_skills
    assert recommended_skills([match.to_dict() for match in matches])[0][0] == "Excel"
