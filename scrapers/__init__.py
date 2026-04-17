"""
Medallion Architecture - Data Pipeline Scrapers & Transformations

This package contains all components for the JobRadar data warehouse
medallion architecture (Bronze → Silver → Gold layers).

Main modules:
    - config: Centralized configuration and constants
    - utils: Shared utility functions and helpers
    - silver_transformation: Bronze → Silver transformation logic
    - gold_transformation: Silver → Gold aggregation logic
    - scrapping_linkedin: LinkedIn job scraper
    - scrapping_france_travail: France-Travail API integration
    - db: Database operations and utilities

Usage:
    from scrapers.config import SKILLS_LIST, TITLE_MAP
    from scrapers.utils import extract_skills, standardize_title
    from scrapers.silver_transformation import transform_bronze_to_silver
    from scrapers.gold_transformation import transform_silver_to_gold
"""

__version__ = "1.0.0"
__author__ = "Medallion Architecture Team"

from .config import (
    SUPABASE_CONFIG,
    get_supabase_headers,
    SKILLS_LIST,
    TITLE_MAP,
    SENIORITY_MAP,
    JOB_CATEGORIES,
    LOCATION_ALIASES,
    PIPELINE_CONFIG,
    VALIDATION_RULES,
    SALARY_CONFIG,
    LOGGING_CONFIG,
    validate_config,
)

from .utils import (
    clean_text,
    standardize_title,
    detect_seniority,
    categorize_job,
    extract_skills,
    normalize_location,
    parse_salary,
    validate_job_record,
    generate_job_id,
    aggregate_keywords,
    compute_seniority_distribution,
    compute_demand_trend,
    fetch_from_supabase,
    write_to_supabase,
)

__all__ = [
    # Configuration
    "SUPABASE_CONFIG",
    "get_supabase_headers",
    "SKILLS_LIST",
    "TITLE_MAP",
    "SENIORITY_MAP",
    "JOB_CATEGORIES",
    "LOCATION_ALIASES",
    "PIPELINE_CONFIG",
    "VALIDATION_RULES",
    "SALARY_CONFIG",
    "LOGGING_CONFIG",
    "validate_config",
    # Utilities
    "clean_text",
    "standardize_title",
    "detect_seniority",
    "categorize_job",
    "extract_skills",
    "normalize_location",
    "parse_salary",
    "validate_job_record",
    "generate_job_id",
    "aggregate_keywords",
    "compute_seniority_distribution",
    "compute_demand_trend",
    "fetch_from_supabase",
    "write_to_supabase",
]
