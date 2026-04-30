"""
Shared Utility Functions
========================

Centralized utility functions used across the Medallion architecture.
This avoids code duplication and improves maintainability.

Import common utilities:
    from scrapers.utils import clean_text, standardize_title, extract_skills
"""

import pandas as pd
import numpy as np
import requests
import hashlib
import re
import logging
from typing import List, Optional, Tuple, Dict
from collections import Counter
from datetime import datetime

from scrapers.config import (
    TITLE_MAP, SENIORITY_MAP, JOB_CATEGORIES, SKILLS_LIST,
    LOCATION_ALIASES, SALARY_CONFIG, PIPELINE_CONFIG,
    get_supabase_headers, SUPABASE_CONFIG, LOGGING_CONFIG
)

# Setup logging
logging.basicConfig(
    format=LOGGING_CONFIG["FORMAT"],
    level=LOGGING_CONFIG["LEVEL"]
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# TEXT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def clean_text(val: any, max_length: int = 500) -> str:
    """Clean and trim text value"""
    if pd.isna(val):
        return ""
    text = str(val).strip()
    # Remove extra whitespace
    text = " ".join(text.split())
    # Limit length
    return text[:max_length]

def to_ascii(val: any) -> str:
    """Remove non-ASCII characters"""
    if not isinstance(val, str):
        val = str(val) if val is not None else ""
    return val.encode("ascii", errors="ignore").decode("ascii").replace("\x00", "")

def standardize_title(title: str) -> str:
    """Standardize job title using regex patterns"""
    if not isinstance(title, str):
        return "Unknown"
    
    t = title.lower().strip()
    
    # Try exact matches first
    for pattern, standard in TITLE_MAP.items():
        if re.search(pattern, t):
            return standard
    
    # Fallback to title case
    return title.title() if title else "Unknown"

def detect_seniority(title: str, description: str = "") -> str:
    """Detect seniority level from title and description"""
    if not isinstance(title, str):
        title = ""
    
    text = f"{title} {description}".lower()
    
    for pattern, level in SENIORITY_MAP.items():
        if re.search(pattern, text):
            return level
    
    return "Mid-level"

def categorize_job(title: str) -> str:
    """Categorize job into business domain"""
    if not isinstance(title, str):
        return "Other"
    
    t = title.lower()
    
    for pattern, category in JOB_CATEGORIES.items():
        if re.search(pattern, t):
            return category
    
    return "Other"

# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_skills(title: str = "", company: str = "", description: str = "") -> List[str]:
    """Extract skills from text fields"""
    text = f"{title} {company} {description}".lower()
    
    # Find all skills present in text
    found_skills = [s for s in SKILLS_LIST if s.lower() in text]
    
    # Remove duplicates while preserving order of appearance
    return list(dict.fromkeys(found_skills))

def aggregate_keywords(keywords_series) -> List[str]:
    """Aggregate and rank keywords from a series"""
    all_keywords = []
    for kw_list in keywords_series:
        if isinstance(kw_list, list):
            all_keywords.extend(kw_list)
        elif isinstance(kw_list, str):
            all_keywords.extend(kw_list.split(","))
    
    if not all_keywords:
        return []
    
    # Return top 10 by frequency
    return [item[0] for item in Counter(all_keywords).most_common(10)]

# ═══════════════════════════════════════════════════════════════════════════════
# LOCATION PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_location(location: str) -> str:
    """Normalize location string"""
    if not location or pd.isna(location):
        return "Non précisé"
    
    loc = str(location).strip().lower()
    
    # Check aliases first
    for key, value in LOCATION_ALIASES.items():
        if key in loc:
            return value
    
    # Take first part before comma or pipe
    loc = loc.split(",")[0].split("|")[0].strip().title()
    
    return loc if loc else "Non précisé"

# ═══════════════════════════════════════════════════════════════════════════════
# SALARY PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def parse_salary(salary_str: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract min and max salary from string"""
    if not salary_str or pd.isna(salary_str):
        return None, None
    
    salary_str = str(salary_str).lower().replace(" ", "")
    
    # Extract all numbers
    numbers = re.findall(r"(\d+(?:\.\d+)?)", salary_str)
    
    if not numbers:
        return None, None
    
    # Convert to float
    numbers = [float(n) for n in numbers]
    
    # Apply K conversion if present
    if "k" in salary_str:
        numbers = [n * 1000 for n in numbers]
    
    # Validate against config
    min_salary = SALARY_CONFIG["MIN_VALID"]
    max_salary = SALARY_CONFIG["MAX_VALID"]
    
    if len(numbers) == 1:
        val = numbers[0]
        if min_salary <= val <= max_salary:
            return val, None
        return None, None
    
    elif len(numbers) >= 2:
        sal_min, sal_max = min(numbers), max(numbers)
        # Validate
        if min_salary <= sal_min <= max_salary and min_salary <= sal_max <= max_salary:
            return sal_min, sal_max
        return None, None
    
    return None, None

def clean_salary_outliers(df: pd.DataFrame, salary_col: str) -> pd.DataFrame:
    """Remove salary outliers using percentile method"""
    percentile = SALARY_CONFIG["OUTLIER_PERCENTILE"]
    threshold = df[salary_col].quantile(percentile / 100)
    
    outliers_removed = (df[salary_col] > threshold).sum()
    df_clean = df[df[salary_col] <= threshold].copy()
    
    if outliers_removed > 0:
        log.info(f"Removed {outliers_removed} salary outliers")
    
    return df_clean

# ═══════════════════════════════════════════════════════════════════════════════
# DATA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_job_record(row: dict) -> Tuple[bool, List[str]]:
    """Validate job record quality"""
    errors = []
    
    # Check required fields
    for field in PIPELINE_CONFIG["REQUIRED_FIELDS"]:
        if not row.get(field) or pd.isna(row.get(field)):
            errors.append(f"Missing {field}")
    
    # Validate title
    title = str(row.get("title", ""))
    if len(title) < PIPELINE_CONFIG["MIN_TITLE_LENGTH"]:
        errors.append(f"Title too short (min {PIPELINE_CONFIG['MIN_TITLE_LENGTH']} chars)")
    if len(title) > PIPELINE_CONFIG["MAX_TITLE_LENGTH"]:
        errors.append(f"Title too long (max {PIPELINE_CONFIG['MAX_TITLE_LENGTH']} chars)")
    
    # Validate company
    company = str(row.get("company", ""))
    if len(company) < PIPELINE_CONFIG["MIN_COMPANY_LENGTH"]:
        errors.append(f"Company too short (min {PIPELINE_CONFIG['MIN_COMPANY_LENGTH']} chars)")
    
    is_valid = len(errors) == 0
    return is_valid, errors

def validate_dataframe(df: pd.DataFrame) -> Tuple[int, int]:
    """Validate entire dataframe and return (valid_count, invalid_count)"""
    if df.empty:
        return 0, 0
    
    validation_results = df.apply(validate_job_record, axis=1)
    valid_count = sum(validation_results.apply(lambda x: x[0]))
    invalid_count = len(df) - valid_count
    
    return valid_count, invalid_count

# ═══════════════════════════════════════════════════════════════════════════════
# UNIQUE IDENTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_job_id(row: dict) -> str:
    """Generate unique job ID from URL or title+company+date"""
    if pd.notna(row.get("job_url")) and row.get("job_url"):
        return hashlib.md5(str(row["job_url"]).encode()).hexdigest()[:16]
    
    # Fallback: hash of title+company+date
    key = f"{row.get('title', '')}{row.get('company', '')}{row.get('scraped_at', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

# ═══════════════════════════════════════════════════════════════════════════════
# AGGREGATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_seniority_distribution(seniority_series) -> dict:
    """Compute distribution of seniority levels"""
    total = len(seniority_series)
    if total == 0:
        return {}
    
    counts = seniority_series.value_counts()
    return {
        level: round((count / total) * 100, 2)
        for level, count in counts.items()
    }

def compute_demand_trend(job_count: int) -> str:
    """Classify job count into demand trend"""
    if job_count >= 100:
        return "HIGH"
    elif job_count >= 30:
        return "MEDIUM"
    else:
        return "LOW"

def compute_salary_stats(salary_series) -> dict:
    """Compute salary statistics"""
    clean_series = salary_series.dropna()
    
    if len(clean_series) == 0:
        return {"mean": None, "median": None, "std": None, "min": None, "max": None}
    
    return {
        "mean": clean_series.mean(),
        "median": clean_series.median(),
        "std": clean_series.std(),
        "min": clean_series.min(),
        "max": clean_series.max(),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE API OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_from_supabase(table: str, limit: int = 1000, offset: int = 0,
                       filters: Dict = None) -> pd.DataFrame:
    """Fetch data from Supabase table"""
    try:
        params = {
            "select": "*",
            "limit": str(limit),
            "offset": str(offset),
        }
        
        # Add filters if provided
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        
        resp = requests.get(
            f"{SUPABASE_CONFIG['URL']}/rest/v1/{table}",
            headers=get_supabase_headers(prefer="count=exact"),
            params=params,
            timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
        )
        
        if resp.status_code in [200, 206]:
            data = resp.json()
            total_count = resp.headers.get("content-range", "/").split("/")[-1]
            log.info(f"Fetched {len(data)} rows from {table} (total: {total_count})")
            return pd.DataFrame(data)
        else:
            log.error(f"Error fetching {table}: {resp.status_code}")
            return pd.DataFrame()
    
    except Exception as e:
        log.error(f"Error fetching from {table}: {str(e)}")
        return pd.DataFrame()

def write_to_supabase(table: str, df: pd.DataFrame, batch_size: int = None) -> int:
    """Write DataFrame to Supabase table (upsert)"""
    if df.empty:
        log.warning(f"No data to write to {table}")
        return 0
    
    batch_size = batch_size or PIPELINE_CONFIG["BATCH_SIZE"]
    
    # Prepare data
    df_export = df.copy()
    
    # Convert datetime columns
    for col in df_export.columns:
        if col.endswith("_at") or col == "date_posted":
            df_export[col] = pd.to_datetime(df_export[col]).astype(str)
    
    # Convert arrays/lists to proper format
    for col in df_export.columns:
        if isinstance(df_export[col].iloc[0] if len(df_export) > 0 else None, list):
            df_export[col] = df_export[col].apply(lambda x: x if isinstance(x, list) else [])
    
    # Replace NaN
    df_export = df_export.where(pd.notna(df_export), None)
    
    records = df_export.to_dict(orient="records")
    written = 0
    
    # Write in batches
    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        
        try:
            resp = requests.post(
                f"{SUPABASE_CONFIG['URL']}/rest/v1/{table}",
                headers=get_supabase_headers(prefer="resolution=merge-duplicates,return=minimal"),
                json=chunk,
                timeout=PIPELINE_CONFIG["TIMEOUT_SECONDS"],
            )
            
            if resp.status_code in [200, 201]:
                written += len(chunk)
                log.info(f"Wrote {len(chunk)} records to {table}")
            else:
                log.error(f"Write error to {table}: {resp.status_code}")
        
        except Exception as e:
            log.error(f"Error writing to {table}: {str(e)}")
    
    return written

# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_dataframe_to_csv(df: pd.DataFrame, filepath: str) -> bool:
    """Export DataFrame to CSV file"""
    try:
        df.to_csv(filepath, index=False, encoding="utf-8")
        log.info(f"Exported {len(df)} rows to {filepath}")
        return True
    except Exception as e:
        log.error(f"Error exporting to CSV: {str(e)}")
        return False

def export_dataframe_to_json(df: pd.DataFrame, filepath: str) -> bool:
    """Export DataFrame to JSON file"""
    try:
        df.to_json(filepath, orient="records", date_format="iso")
        log.info(f"Exported {len(df)} rows to {filepath}")
        return True
    except Exception as e:
        log.error(f"Error exporting to JSON: {str(e)}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# TIMING & PROFILING
# ═══════════════════════════════════════════════════════════════════════════════

def measure_time(func):
    """Decorator to measure function execution time"""
    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = func(*args, **kwargs)
        duration = (datetime.now() - start).total_seconds()
        log.info(f"{func.__name__} completed in {duration:.2f}s")
        return result
    return wrapper

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Text processing
    "clean_text", "to_ascii", "standardize_title", "detect_seniority", "categorize_job",
    
    # Skills
    "extract_skills", "aggregate_keywords",
    
    # Location
    "normalize_location",
    
    # Salary
    "parse_salary", "clean_salary_outliers",
    
    # Validation
    "validate_job_record", "validate_dataframe",
    
    # IDs
    "generate_job_id",
    
    # Aggregation
    "compute_seniority_distribution", "compute_demand_trend", "compute_salary_stats",
    
    # API
    "fetch_from_supabase", "write_to_supabase",
    
    # Export
    "export_dataframe_to_csv", "export_dataframe_to_json",
    
    # Timing
    "measure_time",
]
