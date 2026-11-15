"""Command-line importer for the JobIntel SQLite database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.adzuna import (  # noqa: E402
    AdzunaCredentialsError,
    AdzunaRequestError,
    credentials_from_environment,
    fetch_india_data_jobs,
)
from src.data.database import DATABASE_PATH, upsert_jobs  # noqa: E402
from src.data.loaders import DataLoadError, import_csv_jobs  # noqa: E402

SAMPLE_CSV = PROJECT_ROOT / "data" / "raw" / "sample_jobs.csv"


def parse_args() -> argparse.Namespace:
    """Parse import source and small collection limits for local use."""
    parser = argparse.ArgumentParser(description="Import JobIntel postings into SQLite.")
    parser.add_argument(
        "--source",
        choices=("auto", "csv", "adzuna"),
        default="auto",
        help="auto uses Adzuna only when both credentials are available; otherwise it uses the CSV.",
    )
    parser.add_argument("--csv", type=Path, default=SAMPLE_CSV, help="Path to a job-postings CSV.")
    parser.add_argument(
        "--pages-per-role",
        type=int,
        default=1,
        help="Adzuna result pages per target role; each page requests up to 50 jobs.",
    )
    return parser.parse_args()


def main() -> int:
    """Import API or CSV jobs and describe exactly which source was used."""
    args = parse_args()
    try:
        if args.source in {"auto", "adzuna"}:
            try:
                credentials = credentials_from_environment()
                jobs = fetch_india_data_jobs(credentials, args.pages_per_role)
                imported = upsert_jobs(jobs)
                print(f"Imported {imported} job postings from the Adzuna API into {DATABASE_PATH}.")
                return 0
            except AdzunaCredentialsError:
                if args.source == "adzuna":
                    raise

        result = import_csv_jobs(args.csv)
        print(f"Imported {result.records_processed} job postings from {args.csv} into {result.database_path}.")
        print("This database uses sample/CSV data. The dashboard should label it accordingly.")
        return 0
    except (AdzunaCredentialsError, AdzunaRequestError, DataLoadError, ValueError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
