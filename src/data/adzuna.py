"""Legal Adzuna API collection for India job postings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import requests


class AdzunaCredentialsError(RuntimeError):
    """Raised when API collection is requested without both credentials."""


class AdzunaRequestError(RuntimeError):
    """Raised when the public API cannot return usable job data."""


@dataclass(frozen=True)
class AdzunaCredentials:
    """Credentials kept in environment variables rather than source code."""

    app_id: str
    app_key: str


DEFAULT_TARGET_ROLES = (
    "data scientist",
    "machine learning engineer",
    "data analyst",
    "data engineer",
    "business analyst",
    "business intelligence developer",
    "ai engineer",
    "mlops engineer",
    "data architect",
)


def credentials_from_environment() -> AdzunaCredentials:
    """Load credentials from .env or the active process environment."""
    # CSV imports should remain usable even if optional API dependencies are absent.
    # The dependency is installed by requirements.txt for normal Adzuna use.
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None
    if load_dotenv is not None:
        load_dotenv()
    app_id = os.getenv("ADZUNA_APP_ID", "").strip()
    app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        raise AdzunaCredentialsError(
            "Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env, or use --source csv."
        )
    return AdzunaCredentials(app_id, app_key)


def _city(location: dict[str, Any] | None) -> str:
    """Extract a short city label from Adzuna's location object."""
    display_name = str((location or {}).get("display_name", "")).strip()
    return display_name.split(",")[0].strip() if display_name else ""


def _to_lpa(value: Any) -> float | None:
    """Convert Adzuna annual INR salary values to lakhs per annum."""
    try:
        return round(float(value) / 100_000, 2)
    except (TypeError, ValueError):
        return None


def _to_job_record(result: dict[str, Any]) -> dict[str, Any]:
    """Map one public API response object into the local jobs schema."""
    created = result.get("created")
    posted_date = None
    if created:
        try:
            posted_date = datetime.fromisoformat(str(created).replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            posted_date = None
    return {
        "source_id": f"adzuna-{result.get('id', result.get('redirect_url', 'unknown'))}",
        "source": "Adzuna API",
        "source_type": "api",
        "title": result.get("title", "Untitled role"),
        "company": (result.get("company") or {}).get("display_name", ""),
        "city": _city(result.get("location")),
        "work_mode": "Unspecified",
        "salary_min_lpa": _to_lpa(result.get("salary_min")),
        "salary_max_lpa": _to_lpa(result.get("salary_max")),
        "experience_band": "Unspecified",
        "skills": [],
        "description": result.get("description", ""),
        "posted_date": posted_date,
    }


def fetch_india_data_jobs(
    credentials: AdzunaCredentials,
    pages_per_role: int = 1,
    roles: tuple[str, ...] = DEFAULT_TARGET_ROLES,
) -> pd.DataFrame:
    """Fetch a broad set of data and AI postings from Adzuna India.

    Roles are requested separately so API filtering stays simple and the results
    retain broad coverage across the three portfolio target roles.
    """
    if pages_per_role < 1:
        raise ValueError("pages_per_role must be at least 1.")

    records: list[dict[str, Any]] = []
    for role in roles:
        for page in range(1, pages_per_role + 1):
            try:
                response = requests.get(
                    f"https://api.adzuna.com/v1/api/jobs/in/search/{page}",
                    params={
                        "app_id": credentials.app_id,
                        "app_key": credentials.app_key,
                        "what": role,
                        "results_per_page": 50,
                        "content-type": "application/json",
                    },
                    timeout=20,
                )
                response.raise_for_status()
            except requests.RequestException as error:
                raise AdzunaRequestError(f"Adzuna request failed for '{role}': {error}") from error

            payload = response.json()
            records.extend(_to_job_record(item) for item in payload.get("results", []))

    if not records:
        raise AdzunaRequestError("Adzuna returned no job postings for the requested roles.")
    return pd.DataFrame.from_records(records)
