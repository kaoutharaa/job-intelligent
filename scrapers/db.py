"""""
Database helper — Projet Job Intelligent
Pushes unified job records to Supabase REST API (HTTP).
Called by the Airflow DAG task: push_to_db.

Replaces the old PostgreSQL local connection with Supabase cloud.
Same interface — push_to_postgres() — so the DAG needs zero changes.
"""

import os
import logging
import requests
import pandas as pd

log = logging.getLogger(__name__)

# ─── SUPABASE CONFIG ──────────────────────────────────────────────────────────
# Set these in your docker-compose.yml as environment variables
# OR hardcode here for local dev

SUPABASE_API_URL = os.getenv("SUPABASE_API_URL", "https://egegkouscvcqylndljxp.supabase.co")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "votre_anon_key_ici")

# ─────────────────────────────────────────────────────────────────────────────

# Unified schema columns — must match Supabase jobs table exactly
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


def _headers() -> dict:
    """Supabase REST API headers."""
    return {
        "apikey":        SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=ignore-duplicates,return=minimal",
    }


def _to_ascii(val) -> str:
    """Remove non-ASCII characters to avoid encoding issues."""
    if not isinstance(val, str):
        val = str(val) if val is not None else ""
    return val.encode("ascii", errors="ignore").decode("ascii").replace("\x00", "")


# ─── PUSH FUNCTION ────────────────────────────────────────────────────────────

def push_to_postgres(jobs: list[dict]) -> None:
    """
    Push jobs to Supabase via REST API.
    Named push_to_postgres to keep compatibility with existing DAG — no DAG changes needed.
    """
    if not jobs:
        log.warning("[DB] No jobs to push.")
        return

    if not SUPABASE_API_KEY or SUPABASE_API_KEY == "votre_anon_key_ici":
        log.error("[DB] SUPABASE_API_KEY manquante ! Configurez-la dans docker-compose.yml")
        return

    # Build DataFrame with unified columns
    df = pd.DataFrame(jobs)
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[UNIFIED_COLUMNS]

    # Remove rows with empty job_url
    df = df[df["job_url"].str.strip() != ""]

    # Clean all text columns (ASCII safe for REST API)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(_to_ascii)

    # Replace NaN with None for JSON serialization
    df = df.where(pd.notnull(df), None)
    records = df.to_dict(orient="records")

    log.info(f"[DB] Pushing {len(records)} jobs to Supabase...")

    # Insert in chunks of 100
    chunk_size = 100
    inserted = 0
    skipped  = 0

    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        try:
            resp = requests.post(
                f"{SUPABASE_API_URL}/rest/v1/jobs",
                headers=_headers(),
                json=chunk,
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                inserted += len(chunk)
                log.info(f"[DB] Lot {i//chunk_size + 1}: {inserted}/{len(records)} inseres")
            elif resp.status_code == 409:
                # Duplicates ignored (ON CONFLICT DO NOTHING)
                skipped += len(chunk)
                log.info(f"[DB] Lot {i//chunk_size + 1}: {len(chunk)} doublons ignores")
            else:
                log.error(f"[DB] Erreur lot {i//chunk_size + 1}: {resp.status_code} - {resp.text[:300]}")

        except requests.RequestException as e:
            log.error(f"[DB] Connexion Supabase echouee: {e}")
            break

    log.info(f"[DB] Done - {inserted} inseres, {skipped} doublons ignores.")


# ─── STATS HELPER ─────────────────────────────────────────────────────────────

def get_stats() -> None:
    """Print current row counts from Supabase jobs table."""
    try:
        headers = {
            "apikey":        SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Prefer":        "count=exact",
        }

        # Total count
        resp = requests.get(
            f"{SUPABASE_API_URL}/rest/v1/jobs",
            headers={**headers, "Range": "0-0"},
            timeout=10,
        )
        total = resp.headers.get("Content-Range", "?/?").split("/")[-1]

        # By source
        resp_src = requests.get(
            f"{SUPABASE_API_URL}/rest/v1/jobs",
            headers=headers,
            params={"select": "source", "limit": "1000"},
            timeout=10,
        )

        print(f"\n--- DB Stats (Supabase) ------------------------------------------")
        print(f"Total jobs : {total}")
        if resp_src.status_code == 200:
            sources = pd.DataFrame(resp_src.json())
            if not sources.empty and "source" in sources.columns:
                for src, count in sources["source"].value_counts().items():
                    print(f"  {src:<12}: {count}")
        print("------------------------------------------------------------------\n")

    except Exception as e:
        log.error(f"[DB] Stats error: {e}")