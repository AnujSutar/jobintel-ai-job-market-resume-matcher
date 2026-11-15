"""Semantic and skill-overlap matching between a resume and local jobs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from src.ml.skills import canonicalize_skill


class EmbeddingModelError(RuntimeError):
    """Raised when the local sentence-transformer model cannot be loaded."""


@dataclass(frozen=True)
class JobMatch:
    """One explainable ranked resume-to-job comparison."""

    job_id: int
    title: str
    company: str
    city: str
    work_mode: str
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    semantic_similarity: float
    skill_coverage: float

    def to_dict(self) -> dict[str, Any]:
        """Return a session-state-safe representation for the Streamlit page."""
        return asdict(self)


@lru_cache(maxsize=1)
def load_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> Any:
    """Load the model once; sentence-transformers caches it locally after download."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception as error:
        raise EmbeddingModelError(
            "The matching model could not load. Check the internet connection for its first download, then try again."
        ) from error


def _job_text(job: pd.Series) -> str:
    """Create one compact semantic representation of a posting."""
    skills = ", ".join(str(skill) for skill in job["skills"])
    return "\n".join(
        part for part in (str(job["title"]), str(job["company"]), skills, str(job["description"])) if part
    )


def _overlap(resume_skills: list[str], job_skills: list[str]) -> tuple[list[str], list[str], float]:
    """Calculate explicit skill overlap using canonical labels across sources."""
    resume_set = {canonicalize_skill(skill) for skill in resume_skills}
    ordered_job_skills = [canonicalize_skill(str(skill)) for skill in job_skills]
    matched = [skill for skill in ordered_job_skills if skill in resume_set]
    missing = [skill for skill in ordered_job_skills if skill not in resume_set]
    coverage = len(matched) / len(ordered_job_skills) if ordered_job_skills else 0.0
    return list(dict.fromkeys(matched)), list(dict.fromkeys(missing)), coverage


def rank_jobs(
    resume_text: str,
    resume_skills: list[str],
    jobs: pd.DataFrame,
    top_n: int = 10,
    model: Any | None = None,
) -> list[JobMatch]:
    """Rank jobs using 70% semantic similarity and 30% explicit skill coverage.

    The blend keeps rankings useful for narrative resume content while exposing
    concrete matched and missing skills a student can act on.
    """
    if jobs.empty:
        return []
    model = model or load_embedding_model()
    texts = [resume_text, *[_job_text(job) for _, job in jobs.iterrows()]]
    embeddings = np.asarray(model.encode(texts, normalize_embeddings=True, show_progress_bar=False))
    semantic_scores = np.clip(embeddings[1:] @ embeddings[0], 0.0, 1.0)

    ranked: list[JobMatch] = []
    for (_, job), semantic_score in zip(jobs.iterrows(), semantic_scores):
        matched, missing, coverage = _overlap(resume_skills, job["skills"])
        score = int(round((0.70 * float(semantic_score) + 0.30 * coverage) * 100))
        ranked.append(
            JobMatch(
                job_id=int(job["id"]),
                title=str(job["title"]),
                company=str(job["company"] or "Company not listed"),
                city=str(job["city"] or "Location not listed"),
                work_mode=str(job["work_mode"] or "Unspecified"),
                score=score,
                matched_skills=matched,
                missing_skills=missing,
                semantic_similarity=round(float(semantic_score), 4),
                skill_coverage=round(coverage, 4),
            )
        )
    return sorted(ranked, key=lambda match: (match.score, match.skill_coverage, match.semantic_similarity), reverse=True)[:top_n]


def recommended_skills(matches: list[dict[str, Any]], limit: int = 8) -> list[tuple[str, int]]:
    """Rank missing skills by how many of the displayed jobs require them."""
    counts: dict[str, int] = {}
    for match in matches:
        for skill in match["missing_skills"]:
            counts[skill] = counts.get(skill, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
