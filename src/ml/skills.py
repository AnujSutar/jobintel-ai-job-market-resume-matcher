"""Curated spaCy skill extraction for resumes and job descriptions."""

from __future__ import annotations

from collections import defaultdict

import spacy
from spacy.matcher import PhraseMatcher


SKILL_CATALOG: dict[str, tuple[str, ...]] = {
    "Core Tech": ("Python", "SQL", "Excel", "Power BI", "Tableau", "Statistics", "NumPy"),
    "ML & Data": ("pandas", "scikit-learn", "TensorFlow", "PyTorch", "Spark", "Airflow", "dbt"),
    "GenAI": ("Hugging Face", "LLM", "LangChain", "OpenAI API", "RAG", "NLP"),
    "Cloud & MLOps": ("AWS", "Azure", "GCP", "Docker", "Kubernetes", "MLflow", "FastAPI", "Git"),
}

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql", "structured query language"),
    "Excel": ("excel", "microsoft excel"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Statistics": ("statistics", "statistical analysis"),
    "NumPy": ("numpy",),
    "pandas": ("pandas",),
    "scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Spark": ("spark", "apache spark"),
    "Airflow": ("airflow", "apache airflow"),
    "dbt": ("dbt", "data build tool"),
    "Hugging Face": ("hugging face", "huggingface"),
    "LLM": ("llm", "large language model", "large language models"),
    "LangChain": ("langchain",),
    "OpenAI API": ("openai api", "openai-api"),
    "RAG": ("rag", "retrieval augmented generation"),
    "NLP": ("nlp", "natural language processing"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "GCP": ("gcp", "google cloud platform"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "MLflow": ("mlflow",),
    "FastAPI": ("fastapi", "fast api"),
    "Git": ("git", "github"),
}


def _build_matcher() -> tuple[spacy.language.Language, PhraseMatcher]:
    """Create a lightweight matcher so extraction needs no downloaded spaCy model."""
    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for canonical_name, aliases in SKILL_ALIASES.items():
        matcher.add(canonical_name, [nlp.make_doc(alias) for alias in aliases])
    return nlp, matcher


NLP, SKILL_MATCHER = _build_matcher()
_CANONICAL_BY_CASEFOLD = {
    alias.casefold(): canonical for canonical, aliases in SKILL_ALIASES.items() for alias in aliases
}
_CATEGORY_BY_SKILL = {
    skill: category for category, skills in SKILL_CATALOG.items() for skill in skills
}


def canonicalize_skill(skill: str) -> str:
    """Map aliases from job CSVs or resumes to the same display label."""
    stripped = skill.strip()
    return _CANONICAL_BY_CASEFOLD.get(stripped.casefold(), stripped)


def extract_skills(text: str) -> list[str]:
    """Extract distinct curated skills from text in their first-mentioned order."""
    if not text or not text.strip():
        return []
    document = NLP(text)
    matches = sorted(SKILL_MATCHER(document), key=lambda match: (match[1], match[2]))
    found: list[str] = []
    for match_id, _, _ in matches:
        skill = NLP.vocab.strings[match_id]
        if skill not in found:
            found.append(skill)
    return found


def group_skills(skills: list[str]) -> dict[str, list[str]]:
    """Group found skills for the Resume Matcher UI, retaining uncategorised ones."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for skill in skills:
        grouped[_CATEGORY_BY_SKILL.get(canonicalize_skill(skill), "Other")].append(canonicalize_skill(skill))
    return {category: grouped[category] for category in (*SKILL_CATALOG.keys(), "Other") if grouped[category]}
