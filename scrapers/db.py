"""
Database helper — Projet Job Intelligent (Medallion Architecture)
Pushes raw job records to Bronze layer tables in local PostgreSQL.
Called by the Airflow DAG tasks: push_linkedin_bronze, push_ft_bronze.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)

# ─── CONFIG ────────────────────────────────────────────────────────────────────

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER', 'admin')}:"
    f"{os.getenv('DB_PASS', 'password')}@"
    f"{os.getenv('DB_HOST', 'postgres')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'job_intelligent')}"
)

BRONZE_COLUMNS = [
    "title",
    "company",
    "location",
    "date_posted",
    "job_url",
    "search_keyword",
    "scraped_at",
    "salary",
    "contract_type",
    "source",
]

# ─── BRONZE PUSH ───────────────────────────────────────────────────────────────

def _push_to_bronze(jobs: list[dict], table: str) -> None:
    """Generic function to push raw jobs to a bronze table."""
    if not jobs:
        log.warning(f"[DB] No jobs to push to {table}.")
        return

    engine = create_engine(DB_URL)
    df = pd.DataFrame(jobs)

    for col in BRONZE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[BRONZE_COLUMNS]
    df = df[df["job_url"].str.strip() != ""]

    inserted = 0
    skipped  = 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(
                    text(f"""
                        INSERT INTO {table}
                            (title, company, location, date_posted, job_url,
                             search_keyword, scraped_at, salary, contract_type, source)
                        VALUES
                            (:title, :company, :location, :date_posted, :job_url,
                             :search_keyword, :scraped_at, :salary, :contract_type, :source)
                        ON CONFLICT (job_url) DO NOTHING
                    """),
                    row.to_dict()
                )
                inserted += 1
            except Exception as e:
                log.error(f"[DB] Failed to insert into {table}: {e}")
                skipped += 1

    log.info(f"[DB][{table}] Done — {inserted} inserted, {skipped} skipped.")


def push_linkedin_to_bronze(jobs: list[dict]) -> None:
    """Push raw LinkedIn jobs to bronze_linkedin table."""
    _push_to_bronze(jobs, "bronze_linkedin")


def push_ft_to_bronze(jobs: list[dict]) -> None:
    """Push raw France-Travail jobs to bronze_france_travail table."""
    _push_to_bronze(jobs, "bronze_france_travail")


# ─── STATS HELPER ──────────────────────────────────────────────────────────────

def get_stats() -> None:
    """Print row counts across all medallion layers."""
    try:
        engine = create_engine(DB_URL)
        tables = [
            "bronze_linkedin",
            "bronze_france_travail",
            "silver_linkedin",
            "silver_france_travail",
            "gold_jobs",
        ]

        print(f"\n─── Medallion DB Stats ───────────────────────────────")
        with engine.connect() as conn:
            for table in tables:
                try:
                    count = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()
                    print(f"  {table:<30}: {count} rows")
                except Exception:
                    print(f"  {table:<30}: (table not found)")
        print("──────────────────────────────────────────────────────\n")

    except Exception as e:
        log.error(f"[DB] Stats error: {e}")