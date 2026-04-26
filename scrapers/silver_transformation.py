"""
Medallion Architecture — Bronze to Silver Transformation Layer

SILVER LAYER: Cleaned, validated, and enriched job data

Functions:
  - transform_bronze_to_silver(): Main cleaning pipeline
  - Cleans raw job data from Bronze layer
  - Normalizes location, title, contract type
  - Validates data quality
  - Pushes to Silver layer (silver_jobs table)
"""

import logging
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

from scrapers.config import SUPABASE_CONFIG, get_supabase_headers, PIPELINE_CONFIG
from scrapers.utils import normalize_location, standardize_title

log = logging.getLogger(__name__)
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_bronze_data() -> pd.DataFrame:
    """Fetch all raw jobs from bronze layer"""
    log.info("[SILVER] Fetching Bronze data...")
    all_rows = []
    limit = PIPELINE_CONFIG["BATCH_SIZE"]
    offset = 0

    while True:
        resp = requests.get(
            f"{SUPABASE_CONFIG['URL']}/rest/v1/{PIPELINE_CONFIG['BRONZE_TABLE']}",
            headers=get_supabase_headers(prefer="count=exact"),
            params={
                "select": "*",
                "limit": str(limit),
                "offset": str(offset),
                "order": "scraped_at.desc",
            },
            timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
        )

        if resp.status_code not in [200, 206]:
            log.error(f"[SILVER] Fetch error: {resp.status_code}")
            break

        batch = resp.json()
        if not batch:
            break

        all_rows.extend(batch)
        offset += limit
        if len(batch) < limit:
            break

    if not all_rows:
        log.warning("[SILVER] No Bronze data available")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    log.info(f"[SILVER] Fetched {len(df)} Bronze records")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANING & TRANSFORMATION
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_and_standardize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean, normalize, and enrich job data
    """
    if df.empty:
        log.warning("[SILVER] Empty DataFrame for cleaning")
        return df

    log.info("[SILVER] Cleaning and standardizing data...")

    # ─── Remove duplicates ──────────────────────────────────────────────────────
    initial_count = len(df)
    df = df.drop_duplicates(subset=["job_url"], keep="first")
    log.info(f"[SILVER] Removed {initial_count - len(df)} duplicate records")

    # ─── Remove nulls in critical fields ────────────────────────────────────────
    df = df.dropna(subset=["job_url", "title", "company"])
    log.info(f"[SILVER] Removed records with null critical fields: {len(df)} remaining")

    # ─── Normalize location ─────────────────────────────────────────────────────
    if "location" in df.columns:
        df["location_normalized"] = df["location"].fillna("Unknown").apply(normalize_location)
    else:
        df["location_normalized"] = "Unknown"

    # ─── Standardize job title ─────────────────────────────────────────────────
    if "title" in df.columns:
        df["title_standardized"] = df["title"].fillna("Other").apply(standardize_title)
    else:
        df["title_standardized"] = "Other"

    # ─── Normalize contract type ────────────────────────────────────────────────
    if "contract_type" in df.columns:
        contract_map = {
            "cdi": "CDI", "cdd": "CDD", "stage": "Stage", "freelance": "Freelance",
            "alternance": "Alternance", "apprentissage": "Apprentissage",
            "temps partiel": "Temps partiel", "temps plein": "Temps plein"
        }
        df["contract_type"] = (
            df["contract_type"]
            .fillna("Non spécifié")
            .str.lower()
            .map(lambda x: next((v for k, v in contract_map.items() if k in x.lower()), "Non spécifié"))
        )
    else:
        df["contract_type"] = "Non spécifié"

    # ─── Clean salary fields ────────────────────────────────────────────────────
    if "salary" in df.columns:
        df["salary"] = pd.to_numeric(df["salary"], errors="coerce")

    # ─── Add processing timestamp ────────────────────────────────────────────────
    df["processed_at"] = datetime.utcnow().isoformat()

    # ─── Data quality flag ──────────────────────────────────────────────────────
    df["is_valid"] = (
        (df["job_url"].notna() & df["job_url"].str.len() > 0) &
        (df["title"].notna() & df["title"].str.len() > 0) &
        (df["company"].notna() & df["company"].str.len() > 0)
    )

    valid_count = df["is_valid"].sum()
    invalid_count = (~df["is_valid"]).sum()
    log.info(f"[SILVER] Valid records: {valid_count}, Invalid: {invalid_count}")

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# PUSHING TO SILVER LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def _push_to_silver(df: pd.DataFrame) -> int:
    """
    Push cleaned data to silver_jobs table
    Returns: number of records pushed
    """
    if df.empty:
        log.warning("[SILVER] No data to push to Silver layer")
        return 0

    # Select columns to push
    silver_columns = [
        "job_id", "title", "title_standardized", "company", "location", "location_normalized",
        "contract_type", "salary", "date_posted", "job_url", "source", "search_keyword",
        "scraped_at", "processed_at", "is_valid"
    ]

    # Only push columns that exist
    cols_to_push = [col for col in silver_columns if col in df.columns]
    df_silver = df[cols_to_push].copy()

    # Replace NaN with None for JSON
    df_silver = df_silver.where(pd.notnull(df_silver), None)

    records = df_silver.to_dict(orient="records")

    log.info(f"[SILVER] Pushing {len(records)} records to silver_jobs table...")

    # Insert in chunks of 100
    chunk_size = 100
    total_pushed = 0

    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]

        try:
            resp = requests.post(
                f"{SUPABASE_CONFIG['URL']}/rest/v1/{PIPELINE_CONFIG['SILVER_TABLE']}",
                headers=get_supabase_headers(),
                json=chunk,
                timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
            )

            if resp.status_code not in [201, 409]:  # 201=created, 409=conflict (duplicate)
                log.warning(f"[SILVER] Push error: {resp.status_code} - {resp.text[:200]}")
            else:
                total_pushed += len(chunk)
                log.info(f"[SILVER] Pushed chunk: {total_pushed}/{len(records)}")

        except Exception as e:
            log.error(f"[SILVER] Error pushing chunk: {str(e)}")

    log.info(f"[SILVER] Total records pushed to Silver: {total_pushed}")
    return total_pushed


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TRANSFORMATION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def transform_bronze_to_silver() -> pd.DataFrame:
    """
    Main transformation pipeline: Bronze → Silver

    Steps:
    1. Fetch raw data from BRONZE layer
    2. Clean duplicates, null values
    3. Normalize location, job title, contract type
    4. Validate data quality
    5. Push to SILVER layer (silver_jobs table)

    Returns: Cleaned DataFrame (silver_jobs)
    """
    log.info("[SILVER] ═" * 40)
    log.info("[SILVER] Starting Bronze → Silver transformation...")
    log.info("[SILVER] ═" * 40)

    try:
        # 1. Fetch raw data
        df_bronze = _fetch_bronze_data()
        if df_bronze.empty:
            log.warning("[SILVER] No Bronze data to transform")
            return pd.DataFrame()

        # 2. Clean and standardize
        df_silver = _clean_and_standardize(df_bronze)

        # 3. Push to Silver layer
        pushed = _push_to_silver(df_silver)

        log.info("[SILVER] ═" * 40)
        log.info(f"[SILVER] ✓ Transformation complete")
        log.info(f"[SILVER] ✓ Records processed: {len(df_silver)}")
        log.info(f"[SILVER] ✓ Valid records: {df_silver['is_valid'].sum()}")
        log.info(f"[SILVER] ✓ Records pushed: {pushed}")
        log.info("[SILVER] ═" * 40)

        return df_silver

    except Exception as e:
        log.error(f"[SILVER] Transformation failed: {str(e)}")
        raise
import math
import hashlib
import numpy as np
import pandas as pd
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

from scrapers.config import (
    SUPABASE_CONFIG, get_supabase_headers, PIPELINE_CONFIG
)
from scrapers.utils import (
    clean_text, standardize_title, detect_seniority, categorize_job,
    extract_skills, normalize_location, parse_salary, validate_job_record
)

log = logging.getLogger(__name__)

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# ✅ STRONG UNIQUE ID (FIX 1)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_job_id(row):
    raw = f"{row.get('job_url','')}_{row.get('source','')}"
    return hashlib.md5(raw.encode()).hexdigest()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TRANSFORMATION
# ═══════════════════════════════════════════════════════════════════════════════

def transform_bronze_to_silver() -> pd.DataFrame:
    log.info("[SILVER] Starting Bronze → Silver transformation...")

    # 1. Extract Bronze
    all_rows = []
    limit = PIPELINE_CONFIG["BATCH_SIZE"]
    offset = 0

    while True:
        resp = requests.get(
            f"{SUPABASE_CONFIG['URL']}/rest/v1/{PIPELINE_CONFIG['BRONZE_TABLE']}",
            headers=get_supabase_headers(prefer="count=exact"),
            params={
                "select": "*",
                "limit": str(limit),
                "offset": str(offset),
                "order": "scraped_at.desc",
            },
            timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
        )

        if resp.status_code not in [200, 206]:
            raise Exception(f"[SILVER] Extract error: {resp.status_code}")

        batch = resp.json()
        if not batch:
            break

        all_rows.extend(batch)
        offset += limit

        if len(batch) < limit:
            break

    if not all_rows:
        log.warning("[SILVER] No data in Bronze layer")
        return pd.DataFrame()

    df_bronze = pd.DataFrame(all_rows)
    log.info(f"[SILVER] Extracted {len(df_bronze)} rows")

    # 2. Transform
    df_silver = df_bronze.copy()

    # ✅ Generate deterministic job_id
    df_silver["job_id"] = df_silver.apply(generate_job_id, axis=1)

    # Clean fields
    df_silver["title"] = df_silver["title"].apply(clean_text)
    df_silver["title_standardized"] = df_silver["title"].apply(standardize_title)
    df_silver["company"] = df_silver["company"].apply(clean_text)

    # Location
    df_silver["location_normalized"] = df_silver.get("location", "").apply(normalize_location)

    # Dates
    df_silver["date_posted"] = pd.to_datetime(df_silver.get("date_posted", ""), errors="coerce")

    # Salary
    salary_data = df_silver.get("salary", "").apply(parse_salary)
    df_silver["salary_min"] = salary_data.apply(lambda x: x[0])
    df_silver["salary_max"] = salary_data.apply(lambda x: x[1])
    df_silver["salary_currency"] = df_silver.get("salary_currency", "EUR")

    # Enrichment
    df_silver["seniority_level"] = df_silver.apply(
        lambda row: detect_seniority(row.get("title", ""), row.get("description", "")),
        axis=1
    )

    df_silver["job_category"] = df_silver["title"].apply(categorize_job)

    df_silver["keywords"] = df_silver.apply(
        lambda row: extract_skills(
            row.get("title", ""),
            row.get("company", ""),
            row.get("description", "")
        ),
        axis=1
    )

    # Validation
    validation_data = df_silver.apply(validate_job_record, axis=1)
    df_silver["is_valid"] = validation_data.apply(lambda x: x[0])
    df_silver["validation_errors"] = validation_data.apply(lambda x: x[1])

    df_silver["last_updated"] = datetime.now()

    # Initialize recommender columns
    df_silver["embedding"] = None
    df_silver["embedded_at"] = None

    # ✅ REQUIRED COLUMNS
    required_cols = [
        "job_id", "title", "title_standardized", "company", "location",
        "location_normalized", "date_posted", "scraped_at", "job_url",
        "salary_min", "salary_max", "salary_currency",
        "contract_type", "source", "keywords",
        "job_category", "seniority_level",
        "embedding", "embedded_at",  # for recommender system
        "is_valid", "validation_errors", "last_updated"
    ]

    df_silver = df_silver[[col for col in required_cols if col in df_silver.columns]]
    df_silver["source"] = df_silver["source"].fillna("unknown")

    # ═══════════════════════════════════════════════════════════════════════
    # ✅ FIX 2: GLOBAL DEDUPLICATION (CRITICAL)
    # ═══════════════════════════════════════════════════════════════════════
    before = len(df_silver)
    df_silver = df_silver.drop_duplicates(subset=["job_id"], keep="last")
    after = len(df_silver)

    log.info(f"[SILVER] Removed {before - after} duplicate job_ids")

    # 3. Write
    _write_silver_jobs(df_silver)

    return df_silver

# ═══════════════════════════════════════════════════════════════════════════════
# WRITE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def _write_silver_jobs(df: pd.DataFrame) -> None:
    if df.empty:
        log.warning("[SILVER] No records to write")
        return

    log.info(f"[SILVER] Writing {len(df)} records...")

    # ─── Only select columns that exist in silver_jobs schema ───────────────────
    # Columns in silver_jobs table (excluding auto-generated id)
    valid_columns = [
        "job_id", "title", "title_standardized", "company", "location", 
        "location_normalized", "date_posted", "scraped_at", "job_url",
        "salary_min", "salary_max", "salary_currency", "contract_type",
        "source", "keywords", "job_category", "seniority_level", "is_valid",
        "validation_errors", "last_updated"
    ]
    
    # Only keep columns that exist in the dataframe AND in the schema
    cols_to_write = [col for col in valid_columns if col in df.columns]
    df_json = df[cols_to_write].copy()

    # ─── Format arrays ──────────────────────────────────────────────────────────
    if "keywords" in df_json.columns:
        df_json["keywords"] = df_json["keywords"].apply(lambda x: x if isinstance(x, list) else [])
    if "validation_errors" in df_json.columns:
        df_json["validation_errors"] = df_json["validation_errors"].apply(lambda x: x if isinstance(x, list) else [])

    # ─── Format dates and timestamps ────────────────────────────────────────────
    if "date_posted" in df_json.columns:
        df_json["date_posted"] = df_json["date_posted"].apply(
            lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
        )

    def _format_timestamp(value):
        ts = pd.to_datetime(value, errors="coerce")
        return ts.strftime("%Y-%m-%dT%H:%M:%S") if pd.notna(ts) else None

    def _clean_value(value):
        import numpy as np
        import math
        
        if value is None:
            return None
        if isinstance(value, (np.floating, float)):
            return None if not math.isfinite(value) else float(value)
        if isinstance(value, (np.integer, int)):
            return int(value)
        if isinstance(value, (np.bool_, bool)):
            return bool(value)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return [_clean_value(v) for v in value]
        if isinstance(value, dict):
            return {k: _clean_value(v) for k, v in value.items()}
        if pd.isna(value):
            return None
        return value

    if "scraped_at" in df_json.columns:
        df_json["scraped_at"] = df_json["scraped_at"].apply(_format_timestamp)
    if "last_updated" in df_json.columns:
        df_json["last_updated"] = df_json["last_updated"].apply(
            lambda x: x.strftime("%Y-%m-%dT%H:%M:%S") if pd.notna(x) else None
        )

    df_json = df_json.replace([np.inf, -np.inf], None)
    df_json = df_json.where(pd.notna(df_json), None)

    records = [
        {k: _clean_value(v) for k, v in record.items()}
        for record in df_json.to_dict(orient="records")
    ]

    # ─── Write in chunks ────────────────────────────────────────────────────────
    for chunk in [records[i:i+100] for i in range(0, len(records), 100)]:

        resp = requests.post(
            f"{SUPABASE_CONFIG['URL']}/rest/v1/{PIPELINE_CONFIG['SILVER_TABLE']}",
            headers=get_supabase_headers(prefer="resolution=merge-duplicates,return=minimal"),
            json=chunk,
            timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
        )

        if resp.status_code not in [200, 201]:
            raise Exception(f"[SILVER] Write failed: {resp.status_code} - {resp.text}")

        log.info(f"[SILVER] Wrote {len(chunk)} records")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = transform_bronze_to_silver()
    log.info(f"[SILVER] Pipeline complete - {len(df)} records")