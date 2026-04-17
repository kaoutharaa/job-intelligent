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

    # ✅ REQUIRED COLUMNS
    required_cols = [
        "job_id", "title", "title_standardized", "company", "location",
        "location_normalized", "date_posted", "scraped_at", "job_url",
        "salary_min", "salary_max", "salary_currency",
        "contract_type", "source", "keywords",
        "job_category", "seniority_level",
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

    df_json = df.copy()

    df_json["keywords"] = df_json["keywords"].apply(lambda x: x if isinstance(x, list) else [])
    df_json["validation_errors"] = df_json["validation_errors"].apply(lambda x: x if isinstance(x, list) else [])

    df_json["date_posted"] = df_json["date_posted"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None
    )

    def _format_timestamp(value):
        ts = pd.to_datetime(value, errors="coerce")
        return ts.strftime("%Y-%m-%dT%H:%M:%S") if pd.notna(ts) else None

    def _clean_value(value):
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

    df_json["scraped_at"] = df_json["scraped_at"].apply(_format_timestamp)
    df_json["last_updated"] = df_json["last_updated"].apply(
        lambda x: x.strftime("%Y-%m-%dT%H:%M:%S") if pd.notna(x) else None
    )

    df_json = df_json.replace([np.inf, -np.inf], None)
    df_json = df_json.where(pd.notna(df_json), None)

    records = [
        {k: _clean_value(v) for k, v in record.items()}
        for record in df_json.to_dict(orient="records")
    ]

    # ═══════════════════════════════════════════════════════════════════════
    # WRITE WITH FAIL-FAST (FIX 3)
    # ═══════════════════════════════════════════════════════════════════════
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