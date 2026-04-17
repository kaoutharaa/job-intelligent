# """
# Medallion Architecture — Silver to Gold Transformation Layer

# GOLD LAYER: Aggregated data for analytics and business intelligence

# Functions:
#   - transform_silver_to_gold(): Main aggregation pipeline
#   - Aggregates job market data by title, company, location
#   - Creates dimensions and facts for analytics
#   - Computes trends and market insights
# """

# import numpy as np
# import pandas as pd
# import logging
# import requests
# import json
# from datetime import datetime, date
# from pandas.api.types import is_datetime64_any_dtype
# from typing import Dict, List
# from dotenv import load_dotenv

# from scrapers.config import (
#     SUPABASE_CONFIG, get_supabase_headers, PIPELINE_CONFIG
# )
# from scrapers.utils import (
#     aggregate_keywords, compute_seniority_distribution, 
#     compute_demand_trend
# )

# log = logging.getLogger(__name__)
# load_dotenv()

# # ═══════════════════════════════════════════════════════════════════════════════
# # DATA FETCHING
# # ═══════════════════════════════════════════════════════════════════════════════

# def _fetch_silver_data() -> pd.DataFrame:
#     """Fetch all valid jobs from silver layer"""
#     log.info("[GOLD] Fetching Silver data...")
#     all_rows = []
#     limit = PIPELINE_CONFIG["BATCH_SIZE"]
#     offset = 0
    
#     while True:
#         resp = requests.get(
#             f"{SUPABASE_CONFIG['URL']}/rest/v1/{PIPELINE_CONFIG['SILVER_TABLE']}",
#             headers=get_supabase_headers(prefer="count=exact"),
#             params={
#                 "select": "*",
#                 "is_valid": "eq.true",  # Only valid records
#                 "limit": str(limit),
#                 "offset": str(offset),
#                 "order": "scraped_at.desc",
#             },
#             timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
#         )
        
#         if resp.status_code not in [200, 206]:
#             log.error(f"[GOLD] Fetch error: {resp.status_code}")
#             break
        
#         batch = resp.json()
#         if not batch:
#             break
        
#         all_rows.extend(batch)
#         offset += limit
#         if len(batch) < limit:
#             break
    
#     if not all_rows:
#         log.warning("[GOLD] No Silver data available")
#         return pd.DataFrame()
    
#     df = pd.DataFrame(all_rows)
#     log.info(f"[GOLD] Fetched {len(df)} Silver records")
#     return df

# # ═══════════════════════════════════════════════════════════════════════════════
# # GOLD TRANSFORMATIONS
# # ═══════════════════════════════════════════════════════════════════════════════

# def _create_daily_snapshot(df: pd.DataFrame) -> pd.DataFrame:
#     """Create daily job market snapshot aggregation"""
#     log.info("[GOLD] Creating daily snapshot...")
    
#     if df.empty:
#         return pd.DataFrame()
    
#     today = datetime.now().date()
    
#     # Aggregate by source and title
#     snapshot = df.groupby(["source", "title_standardized"]).agg({
#         "job_id": "count",
#         "salary_min": "mean",
#         "salary_max": "mean",
#         "location_normalized": lambda x: list(x.value_counts().head(5).index),
#         "company": lambda x: list(x.value_counts().head(5).index),
#         "contract_type": lambda x: list(x.value_counts().head(3).index) if len(x) > 0 else [],
#     }).reset_index()
    
#     snapshot.columns = [
#         "source", "title_standardized", "total_jobs", "avg_salary_min",
#         "avg_salary_max", "locations", "top_companies", "dominant_contract_types"
#     ]
    
#     snapshot["snapshot_date"] = today
#     snapshot["created_at"] = datetime.now()
    
#     return snapshot

# def _create_company_stats(df: pd.DataFrame) -> pd.DataFrame:
#     """Create company dimension with aggregates"""
#     log.info("[GOLD] Creating company statistics...")
    
#     if df.empty:
#         return pd.DataFrame()
    
#     company_stats = df.groupby("company").agg({
#         "job_id": "count",
#         "salary_min": "mean",
#         "salary_max": "mean",
#         "title_standardized": lambda x: list(x.value_counts().head(5).index),
#     }).reset_index()
    
#     company_stats.columns = ["company", "total_jobs", "avg_salary_min", "avg_salary_max", "top_titles"]
#     company_stats["last_updated"] = datetime.now()
#     company_stats["created_at"] = datetime.now()
    
#     return company_stats

# def _create_location_stats(df: pd.DataFrame) -> pd.DataFrame:
#     """Create location dimension with aggregates"""
#     log.info("[GOLD] Creating location statistics...")
    
#     if df.empty:
#         return pd.DataFrame()
    
#     location_stats = df.groupby("location_normalized").agg({
#         "job_id": "count",
#         "salary_min": "mean",
#         "salary_max": "mean",
#         "title_standardized": lambda x: list(x.value_counts().head(5).index),
#         "company": lambda x: list(x.value_counts().head(5).index),
#     }).reset_index()
    
#     location_stats.columns = [
#         "location", "total_jobs", "avg_salary_min", "avg_salary_max",
#         "top_titles", "top_companies"
#     ]
#     location_stats["last_updated"] = datetime.now()
#     location_stats["created_at"] = datetime.now()
    
#     return location_stats

# def _create_job_title_insights(df: pd.DataFrame) -> pd.DataFrame:
#     """Create job title dimension with market insights"""
#     log.info("[GOLD] Creating job title insights...")
    
#     if df.empty:
#         return pd.DataFrame()
    
#     title_insights = df.groupby("title_standardized").agg({
#         "job_id": "count",
#         "salary_min": ["mean", "median"],
#         "salary_max": ["mean", "median"],
#         "company": lambda x: list(x.value_counts().head(5).index),
#         "location_normalized": lambda x: list(x.value_counts().head(5).index),
#         "contract_type": lambda x: list(x.value_counts().head(3).index),
#         "keywords": lambda x: aggregate_keywords(x),  # Using centralized function
#         "seniority_level": lambda x: compute_seniority_distribution(x),  # Using centralized function
#     }).reset_index()
    
#     # Flatten column names
#     title_insights.columns = [
#         "title_standardized", "total_jobs", "avg_salary_min", "median_salary_min",
#         "avg_salary_max", "median_salary_max", "top_companies", "top_locations",
#         "common_contract_types", "common_keywords", "seniority_distribution"
#     ]
    
#     # Use median as salary_median
#     title_insights["salary_median"] = (
#         title_insights["median_salary_min"] + title_insights["median_salary_max"]
#     ) / 2
    
#     # Compute market demand trend using centralized function
#     title_insights["market_demand_trend"] = title_insights["total_jobs"].apply(compute_demand_trend)
    
#     title_insights["last_updated"] = datetime.now()
#     title_insights["created_at"] = datetime.now()
    
#     return title_insights

# def _create_monthly_trends(df: pd.DataFrame) -> pd.DataFrame:
#     """Create monthly trend fact table"""
#     log.info("[GOLD] Creating monthly trends...")
    
#     if df.empty:
#         return pd.DataFrame()
    
#     # Convert scraped_at to datetime
#     df["scraped_at"] = pd.to_datetime(df["scraped_at"])
#     df["year_month"] = df["scraped_at"].dt.to_period("M").dt.to_timestamp()
    
#     trends = df.groupby(["year_month", "source"]).agg({
#         "job_id": "count",
#         "company": lambda x: x.nunique(),
#         "salary_min": "mean",
#         "salary_max": "mean",
#         "title_standardized": lambda x: list(x.value_counts().head(5).index),
#         "location_normalized": lambda x: list(x.value_counts().head(5).index),
#     }).reset_index()
    
#     trends.columns = [
#         "year_month", "source", "new_jobs_count", "unique_companies",
#         "avg_salary_min", "avg_salary_max", "top_job_titles", "top_locations"
#     ]
    
#     trends["created_at"] = datetime.now()
    
#     return trends

# # ═══════════════════════════════════════════════════════════════════════════════
# # WRITE OPERATIONS
# # ═══════════════════════════════════════════════════════════════════════════════

# def _write_table(table_name: str, df: pd.DataFrame) -> int:
#     """Upsert DataFrame to Supabase table"""
#     if df.empty:
#         log.warning(f"[GOLD] No records for {table_name}")
#         return 0
    
#     log.info(f"[GOLD] Writing {len(df)} records to {table_name}...")
    
#     # Convert types to JSON-serializable
#     df_json = df.copy()
    
#     for col in df_json.columns:
#         if is_datetime64_any_dtype(df_json[col]):
#             df_json[col] = pd.to_datetime(df_json[col]).dt.strftime("%Y-%m-%dT%H:%M:%S")
#         elif col == "year_month":
#             df_json[col] = pd.to_datetime(df_json[col]).dt.strftime("%Y-%m-%d")
#         else:
#             df_json[col] = df_json[col].apply(
#                 lambda v: v.strftime("%Y-%m-%dT%H:%M:%S") if isinstance(v, datetime)
#                 else (v.strftime("%Y-%m-%d") if isinstance(v, date) else v)
#             )
    
#     # Convert lists to JSON
#     for col in df_json.columns:
#         if df_json[col].dtype == "object":
#             try:
#                 if isinstance(df_json[col].iloc[0], list):
#                     df_json[col] = df_json[col].apply(lambda x: x if isinstance(x, list) else [])
#             except (IndexError, TypeError):
#                 pass

#     # Replace NaN / inf values with None
#     df_json = df_json.replace([np.inf, -np.inf], None)
#     df_json = df_json.where(pd.notna(df_json), None)
#     df_json = df_json.applymap(lambda x: None if isinstance(x, float) and (np.isinf(x) or np.isnan(x)) else x)
    
#     import math

# def _clean_value(value):
#     if value is None:
#         return None

#     # ✅ FIX: handle NaN / inf safely
#     if isinstance(value, (float, np.floating)):
#         if not math.isfinite(value):
#             return None
#         return float(value)

#     if isinstance(value, (np.integer, int)):
#         return int(value)

#     if isinstance(value, (np.bool_, bool)):
#         return bool(value)

#     # Dates
#     if isinstance(value, (datetime, date)):
#         return value.strftime("%Y-%m-%dT%H:%M:%S") if isinstance(value, datetime) else value.strftime("%Y-%m-%d")

#     # Lists
#     if isinstance(value, list):
#         return [_clean_value(v) for v in value]

#     # Dicts
#     if isinstance(value, dict):
#         return {k: _clean_value(v) for k, v in value.items()}

#     # Pandas NaN fallback
#     if pd.isna(value):
#         return None

#     return value


#     records = [
#     {k: _clean_value(v) for k, v in record.items()}
#     for record in df_json.to_dict(orient="records")
# ]
#     written = 0
    
#     # Batch write
#     for chunk in [records[i:i+100] for i in range(0, len(records), 100)]:
#         json_str = json.dumps(chunk, default=lambda x: None if isinstance(x, float) and not math.isfinite(x) else x)
#         resp = requests.post(
#             f"{SUPABASE_CONFIG['URL']}/rest/v1/{table_name}",
#             headers=get_supabase_headers(prefer="resolution=merge-duplicates,return=minimal"),
#             data=json_str,
#             timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
#         )
        
#         if resp.status_code not in [200, 201]:
#             log.error(f"[GOLD] Write error to {table_name}: {resp.status_code} - {resp.text[:300]}")
#         else:
#             written += len(chunk)
#             log.info(f"[GOLD] Wrote {len(chunk)} records to {table_name}")
    
#     return written

# # ═══════════════════════════════════════════════════════════════════════════════
# # MAIN PIPELINE
# # ═══════════════════════════════════════════════════════════════════════════════

# def transform_silver_to_gold() -> Dict[str, int]:
#     """
#     Main transformation: Silver → Gold (aggregations and insights)
    
#     Returns:
#         Dictionary with rows written per table
#     """
#     log.info("[GOLD] Starting Silver → Gold transformation...")
#     results = {}
    
#     # 1. Fetch Silver data
#     df_silver = _fetch_silver_data()
#     if df_silver.empty:
#         log.warning("[GOLD] No Silver data to aggregate")
#         return results
    
#     # 2. Create aggregations
#     daily_snapshot = _create_daily_snapshot(df_silver)
#     company_stats = _create_company_stats(df_silver)
#     location_stats = _create_location_stats(df_silver)
#     title_insights = _create_job_title_insights(df_silver)
#     monthly_trends = _create_monthly_trends(df_silver)
    
#     # 3. Write to Gold tables using centralized config
#     gold_tables = PIPELINE_CONFIG["GOLD_TABLES"]
#     results[gold_tables["snapshots"]] = _write_table(gold_tables["snapshots"], daily_snapshot)
#     results[gold_tables["companies"]] = _write_table(gold_tables["companies"], company_stats)
#     results[gold_tables["locations"]] = _write_table(gold_tables["locations"], location_stats)
#     results[gold_tables["titles"]] = _write_table(gold_tables["titles"], title_insights)
#     results[gold_tables["trends"]] = _write_table(gold_tables["trends"], monthly_trends)
    
#     log.info(f"[GOLD] Pipeline complete: {results}")
#     return results

# if __name__ == "__main__":
#     import logging
    
#     logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
#     results = transform_silver_to_gold()
#     for table, count in results.items():
#         print(f"{table}: {count} rows written")



 




"""
Medallion Architecture — Silver to Gold Transformation Layer

GOLD LAYER: Aggregated data for analytics and business intelligence

Functions:
  - transform_silver_to_gold(): Main aggregation pipeline
  - Aggregates job market data by title, company, location
  - Creates dimensions and facts for analytics
  - Computes trends and market insights
"""

import math
import json
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, date
from pandas.api.types import is_datetime64_any_dtype
from typing import Dict
from dotenv import load_dotenv

from scrapers.config import (
    SUPABASE_CONFIG, get_supabase_headers, PIPELINE_CONFIG
)
from scrapers.utils import (
    aggregate_keywords, compute_seniority_distribution,
    compute_demand_trend
)

log = logging.getLogger(__name__)
load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_silver_data() -> pd.DataFrame:
    """Fetch all valid jobs from silver layer"""
    log.info("[GOLD] Fetching Silver data...")
    all_rows = []
    limit = PIPELINE_CONFIG["BATCH_SIZE"]
    offset = 0

    while True:
        resp = requests.get(
            f"{SUPABASE_CONFIG['URL']}/rest/v1/{PIPELINE_CONFIG['SILVER_TABLE']}",
            headers=get_supabase_headers(prefer="count=exact"),
            params={
                "select": "*",
                "is_valid": "eq.true",
                "limit": str(limit),
                "offset": str(offset),
                "order": "scraped_at.desc",
            },
            timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
        )

        if resp.status_code not in [200, 206]:
            log.error(f"[GOLD] Fetch error: {resp.status_code}")
            break

        batch = resp.json()
        if not batch:
            break

        all_rows.extend(batch)
        offset += limit
        if len(batch) < limit:
            break

    if not all_rows:
        log.warning("[GOLD] No Silver data available")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    log.info(f"[GOLD] Fetched {len(df)} Silver records")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# GOLD TRANSFORMATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _create_daily_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Create daily job market snapshot aggregation"""
    log.info("[GOLD] Creating daily snapshot...")

    if df.empty:
        return pd.DataFrame()

    today = datetime.now().date()

    snapshot = df.groupby(["source", "title_standardized"]).agg({
        "job_id": "count",
        "salary_min": "mean",
        "salary_max": "mean",
        "location_normalized": lambda x: list(x.value_counts().head(5).index),
        "company": lambda x: list(x.value_counts().head(5).index),
        "contract_type": lambda x: list(x.value_counts().head(3).index) if len(x) > 0 else [],
    }).reset_index()

    snapshot.columns = [
        "source", "title_standardized", "total_jobs", "avg_salary_min",
        "avg_salary_max", "locations", "top_companies", "dominant_contract_types"
    ]

    snapshot["snapshot_date"] = today
    snapshot["created_at"] = datetime.now()

    return snapshot


def _create_company_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Create company dimension with aggregates"""
    log.info("[GOLD] Creating company statistics...")

    if df.empty:
        return pd.DataFrame()

    company_stats = df.groupby("company").agg({
        "job_id": "count",
        "salary_min": "mean",
        "salary_max": "mean",
        "title_standardized": lambda x: list(x.value_counts().head(5).index),
    }).reset_index()

    company_stats.columns = ["company", "total_jobs", "avg_salary_min", "avg_salary_max", "top_titles"]
    company_stats["last_updated"] = datetime.now()
    company_stats["created_at"] = datetime.now()

    return company_stats


def _create_location_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Create location dimension with aggregates"""
    log.info("[GOLD] Creating location statistics...")

    if df.empty:
        return pd.DataFrame()

    location_stats = df.groupby("location_normalized").agg({
        "job_id": "count",
        "salary_min": "mean",
        "salary_max": "mean",
        "title_standardized": lambda x: list(x.value_counts().head(5).index),
        "company": lambda x: list(x.value_counts().head(5).index),
    }).reset_index()

    location_stats.columns = [
        "location", "total_jobs", "avg_salary_min", "avg_salary_max",
        "top_titles", "top_companies"
    ]
    location_stats["last_updated"] = datetime.now()
    location_stats["created_at"] = datetime.now()

    return location_stats


def _create_job_title_insights(df: pd.DataFrame) -> pd.DataFrame:
    """Create job title dimension with market insights"""
    log.info("[GOLD] Creating job title insights...")

    if df.empty:
        return pd.DataFrame()

    title_insights = df.groupby("title_standardized").agg({
        "job_id": "count",
        "salary_min": ["mean", "median"],
        "salary_max": ["mean", "median"],
        "company": lambda x: list(x.value_counts().head(5).index),
        "location_normalized": lambda x: list(x.value_counts().head(5).index),
        "contract_type": lambda x: list(x.value_counts().head(3).index),
        "keywords": lambda x: aggregate_keywords(x),
        "seniority_level": lambda x: compute_seniority_distribution(x),
    }).reset_index()

    # Flatten column names
    title_insights.columns = [
        "title_standardized", "total_jobs", "avg_salary_min", "median_salary_min",
        "avg_salary_max", "median_salary_max", "top_companies", "top_locations",
        "common_contract_types", "common_keywords", "seniority_distribution"
    ]

    title_insights["salary_median"] = (
    title_insights["median_salary_min"] + title_insights["median_salary_max"]
) / 2

    title_insights = title_insights.drop(columns=["median_salary_min", "median_salary_max"])

    title_insights["market_demand_trend"] = title_insights["total_jobs"].apply(compute_demand_trend)

 
    title_insights["last_updated"] = datetime.now()
    title_insights["created_at"] = datetime.now()

    return title_insights


def _create_monthly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Create monthly trend fact table"""
    log.info("[GOLD] Creating monthly trends...")

    if df.empty:
        return pd.DataFrame()

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df["year_month"] = df["scraped_at"].dt.to_period("M").dt.to_timestamp()

    trends = df.groupby(["year_month", "source"]).agg({
        "job_id": "count",
        "company": lambda x: x.nunique(),
        "salary_min": "mean",
        "salary_max": "mean",
        "title_standardized": lambda x: list(x.value_counts().head(5).index),
        "location_normalized": lambda x: list(x.value_counts().head(5).index),
    }).reset_index()

    trends.columns = [
        "year_month", "source", "new_jobs_count", "unique_companies",
        "avg_salary_min", "avg_salary_max", "top_job_titles", "top_locations"
    ]

    trends["created_at"] = datetime.now()

    return trends


# ═══════════════════════════════════════════════════════════════════════════════
# WRITE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_value(value):
    """Recursively clean a value to be JSON-serializable."""
    if value is None:
        return None

    if isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            return None
        return float(value)

    if isinstance(value, (np.integer, int)):
        return int(value)

    if isinstance(value, (np.bool_, bool)):
        return bool(value)

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, list):
        return [_clean_value(v) for v in value]

    if isinstance(value, dict):
        return {k: _clean_value(v) for k, v in value.items()}

    # Guard pd.isna() — can raise on non-scalar types
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value

def _write_table(table_name: str, df: pd.DataFrame, on_conflict: str = None) -> int:
    """Upsert DataFrame to Supabase table"""
    if df.empty:
        log.warning(f"[GOLD] No records for {table_name}")
        return 0

    log.info(f"[GOLD] Writing {len(df)} records to {table_name}...")

    df_json = df.copy()

    # Convert datetime columns to ISO strings
    for col in df_json.columns:
        if is_datetime64_any_dtype(df_json[col]):
            df_json[col] = pd.to_datetime(df_json[col]).dt.strftime("%Y-%m-%dT%H:%M:%S")
        elif col == "year_month":
            df_json[col] = pd.to_datetime(df_json[col]).dt.strftime("%Y-%m-%d")

    # Replace NaN / inf with None
    df_json = df_json.replace([np.inf, -np.inf], None)
    df_json = df_json.where(pd.notna(df_json), None)
    # Fix: .map() replaces deprecated .applymap() in pandas 2.1+
    df_json = df_json.map(
        lambda x: None if isinstance(x, float) and not math.isfinite(x) else x
    )

    records = [
        {k: _clean_value(v) for k, v in record.items()}
        for record in df_json.to_dict(orient="records")
    ]

    written = 0

    for chunk in [records[i:i + 100] for i in range(0, len(records), 100)]:
        json_str = json.dumps(
            chunk,
            default=lambda x: None if isinstance(x, float) and not math.isfinite(x) else x,
        )
        resp = requests.post(
    f"{SUPABASE_CONFIG['URL']}/rest/v1/{table_name}",
    headers=get_supabase_headers(prefer="resolution=merge-duplicates,return=minimal"),
    params={"on_conflict": on_conflict} if on_conflict else {},
    data=json_str,
    timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
)

        if resp.status_code not in [200, 201]:
            log.error(f"[GOLD] Write error to {table_name}: {resp.status_code} - {resp.text[:300]}")
        else:
            written += len(chunk)
            log.info(f"[GOLD] Wrote {len(chunk)} records to {table_name}")

    return written


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def transform_silver_to_gold() -> Dict[str, int]:
    """
    Main transformation: Silver → Gold (aggregations and insights)

    Returns:
        Dictionary with rows written per table
    """
    log.info("[GOLD] Starting Silver → Gold transformation...")
    results = {}

    # 1. Fetch Silver data
    df_silver = _fetch_silver_data()
    if df_silver.empty:
        log.warning("[GOLD] No Silver data to aggregate")
        return results

    # 2. Create aggregations
    daily_snapshot = _create_daily_snapshot(df_silver)
    company_stats = _create_company_stats(df_silver)
    location_stats = _create_location_stats(df_silver)
    title_insights = _create_job_title_insights(df_silver)
    monthly_trends = _create_monthly_trends(df_silver)

    # 3. Write to Gold tables
    gold_tables = PIPELINE_CONFIG["GOLD_TABLES"]
    results[gold_tables["snapshots"]] = _write_table(gold_tables["snapshots"], daily_snapshot)
    results[gold_tables["companies"]] = _write_table(gold_tables["companies"], company_stats, on_conflict="company")
    results[gold_tables["locations"]] = _write_table(gold_tables["locations"], location_stats, on_conflict="location")
    results[gold_tables["titles"]]    = _write_table(gold_tables["titles"], title_insights, on_conflict="title_standardized")
    results[gold_tables["trends"]] = _write_table(gold_tables["trends"], monthly_trends, on_conflict="year_month,source")

    log.info(f"[GOLD] Pipeline complete: {results}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results = transform_silver_to_gold()
    for table, count in results.items():
        print(f"{table}: {count} rows written")