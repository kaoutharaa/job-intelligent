"""
Database helper — Projet Job Intelligent
Pushes unified job records to PostgreSQL.
Called by the Airflow DAG task: push_to_db.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)

# ─── CONFIG ────────────────────────────────────────────────────────────────────

# All values read from environment variables set in docker-compose.yml
DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER', 'admin')}:"
    f"{os.getenv('DB_PASS', 'password')}@"
    f"{os.getenv('DB_HOST', 'postgres')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'job_intelligent')}"
)

# Unified schema columns — must match sql/init.sql exactly
UNIFIED_COLUMNS = [
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

# ─── PUSH FUNCTION ─────────────────────────────────────────────────────────────

def push_to_postgres(jobs: list[dict]) -> None:
    if not jobs:
        log.warning("[DB] No jobs to push.")
        return

    engine = create_engine(DB_URL)
    df = pd.DataFrame(jobs)

    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[UNIFIED_COLUMNS]
    df = df[df["job_url"].str.strip() != ""]

    inserted = 0
    skipped  = 0

    with engine.begin() as conn:          # ← engine.begin() auto-commits on exit
        for _, row in df.iterrows():
            try:
                conn.execute(
                    text("""
                        INSERT INTO jobs
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
                log.error(f"[DB] Failed to insert row: {e}")
                skipped += 1

    log.info(f"[DB] Done — {inserted} inserted, {skipped} skipped (duplicates/errors).")


# ─── STATS HELPER (optional, useful for debugging) ────────────────────────────

def get_stats() -> None:
    """Print current row counts from the jobs table."""
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        total   = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
        by_src  = conn.execute(
            text("SELECT source, COUNT(*) FROM jobs GROUP BY source")
        ).fetchall()

    print(f"\n─── DB Stats ─────────────────────────────────────")
    print(f"Total jobs : {total}")
    for src, count in by_src:
        print(f"  {src:<12}: {count}")
    print("──────────────────────────────────────────────────\n")