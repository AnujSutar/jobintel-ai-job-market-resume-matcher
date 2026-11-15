"""Resume-informed outbound job searches and actionable learning guidance."""

from __future__ import annotations

from urllib.parse import quote_plus


IMPROVEMENT_GUIDANCE = {
    "Python": "Build and document one data project that uses clean functions, tests, and a README.",
    "SQL": "Practise joins, window functions, and business-style analysis questions using a public dataset.",
    "Excel": "Learn pivot tables, XLOOKUP, charts, and concise business reporting.",
    "Power BI": "Publish one dashboard with calculated measures and a clear written insight section.",
    "Tableau": "Build an interactive dashboard and explain the decisions behind each chart.",
    "scikit-learn": "Train, evaluate, and compare baseline models with reproducible notebooks or scripts.",
    "TensorFlow": "Complete a small deep-learning project and document the dataset, metrics, and limitations.",
    "PyTorch": "Implement and evaluate a compact neural-network project, then publish the code and results.",
    "Spark": "Learn DataFrame transformations and build a small batch-processing example.",
    "Airflow": "Create a simple scheduled data pipeline with clear tasks, retries, and logs.",
    "AWS": "Deploy a small data or ML service and document its architecture and cost-conscious choices.",
    "Azure": "Deploy a data or ML workflow and document the services used and their purpose.",
    "GCP": "Build a small cloud data workflow and explain its storage, compute, and permissions choices.",
    "Docker": "Containerise one portfolio project with a reproducible run command.",
    "Kubernetes": "Learn deployment, service, and configuration basics after you are comfortable with Docker.",
    "MLflow": "Track experiments, parameters, and metrics for a machine-learning project.",
    "FastAPI": "Expose a small model or data utility through documented API endpoints.",
    "Hugging Face": "Create a small NLP or transformer demo and document the model, data, and evaluation.",
}


def build_search_query(role: str, resume_skills: list[str], max_skills: int = 2) -> str:
    """Create a concise platform-search query from a target role and known skills."""
    useful_skills = [skill for skill in resume_skills if skill][:max_skills]
    return " ".join([role, *useful_skills]).strip()


def platform_search_urls(query: str, city: str) -> dict[str, str]:
    """Return normal outbound search URLs without collecting platform results."""
    location = city if city != "All India" else "India"
    query_parameter = quote_plus(query)
    location_parameter = quote_plus(location)
    naukri_query = "-".join(part for part in query.lower().split() if part.isalnum())
    naukri_location = "india" if city == "All India" else "-".join(part for part in city.lower().split() if part.isalnum())
    return {
        "LinkedIn Jobs": f"https://www.linkedin.com/jobs/search/?keywords={query_parameter}&location={location_parameter}",
        "Indeed India": f"https://in.indeed.com/jobs?q={query_parameter}&l={location_parameter}",
        "Naukri": f"https://www.naukri.com/{naukri_query}-jobs-in-{naukri_location}",
    }


def improvement_plan(recommendations: list[tuple[str, int]], limit: int = 5) -> list[tuple[str, int, str]]:
    """Attach a practical next action to skills missing from top local matches."""
    plan: list[tuple[str, int, str]] = []
    for skill, job_count in recommendations[:limit]:
        guidance = IMPROVEMENT_GUIDANCE.get(
            skill,
            "Learn the fundamentals, apply the skill in a small portfolio project, and describe the outcome on your resume.",
        )
        plan.append((skill, job_count, guidance))
    return plan
