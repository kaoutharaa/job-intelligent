"""
Centralized Configuration & Constants
=======================================

This module consolidates all configuration, patterns, and constants used across
the Medallion architecture to avoid repetition and improve maintainability.

Import this module to access shared configurations:
    from scrapers.config import SKILLS_LIST, TITLE_MAP, SUPABASE_CONFIG
"""

import os
from typing import Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SUPABASE_CONFIG = {
    "URL": os.getenv("SUPABASE_API_URL", "https://egegkouscvcqylndljxp.supabase.co"),
    "API_KEY": os.getenv("SUPABASE_API_KEY", ""),
}

def get_supabase_headers(prefer: str = "return=minimal") -> dict:
    """Create Supabase API headers"""
    return {
        "apikey": SUPABASE_CONFIG["API_KEY"],
        "Authorization": f"Bearer {SUPABASE_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

SKILLS_LIST = [
    # Data & Analytics
    "python", "sql", "r", "julia", "scala", "spark", "hadoop", "kafka",
    "airflow", "dbt", "luigi", "prefect", "dagster",
    
    # BI & Visualization
    "power bi", "tableau", "excel", "lookahead", "metabase", "superset",
    
    # Cloud & Infrastructure
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
    
    # ML & AI
    "tensorflow", "pytorch", "scikit-learn", "mlflow", "xgboost",
    "keras", "opencv", "huggingface", "ray",
    
    # Data Processing
    "pandas", "numpy", "polars", "dask", "vaex",
    
    # Web Frameworks
    "fastapi", "flask", "django", "sqlalchemy", "rest api",
    
    # Frontend
    "react", "node", "javascript", "typescript", "vue", "angular",
    
    # Database
    "postgresql", "mongodb", "redis", "elasticsearch", "snowflake",
    "bigquery", "cassandra", "neo4j", "dynamodb", "athena",
    
    # DevOps & System
    "git", "linux", "ci/cd", "jenkins", "github actions", "gitlab ci",
    "grafana", "prometheus", "datadog", "newrelic",
    
    # Development
    "java", "go", "rust", "c++", "c#", "dotnet", "php",
    
    # Security & Compliance
    "security", "encryption", "oauth", "saml", "audit", "gdpr",
]

# ═══════════════════════════════════════════════════════════════════════════════
# JOB TITLE STANDARDIZATION
# ═══════════════════════════════════════════════════════════════════════════════

TITLE_MAP = {
    # Data Science & Analytics
    r"data scien.*": "Data Scientist",
    r"data engin.*": "Data Engineer",
    r"data analy.*": "Data Analyst",
    r"analytics engin.*": "Analytics Engineer",
    r"(analytics|data) architect.*": "Data Architect",
    
    # Machine Learning
    r"machine learn.*": "ML Engineer",
    r"deep learn.*": "ML Engineer",
    r"ai engin.*": "AI Engineer",
    r"nlp.*": "NLP Engineer",
    r"computer vision.*": "Computer Vision Engineer",
    r"mlops.*": "MLOps Engineer",
    
    # Business Intelligence
    r"bi anal.*": "BI Analyst",
    r"business intel.*": "BI Analyst",
    r"analytics specialist.*": "Analytics Specialist",
    
    # DevOps & Cloud
    r"devops.*": "DevOps Engineer",
    r"cloud engin.*": "Cloud Engineer",
    r"sre.*": "Site Reliability Engineer",
    r"platform engin.*": "Platform Engineer",
    r"infrastructure.*": "Infrastructure Engineer",
    
    # Software Development
    r"software engin.*": "Software Engineer",
    r"backend.*": "Backend Developer",
    r"frontend.*": "Frontend Developer",
    r"full.?stack.*": "Full Stack Developer",
    r"mobile.*": "Mobile Developer",
    r"web.*dev.*": "Web Developer",
    
    # Security
    r"cybersec.*": "Cybersecurity Engineer",
    r"security analyst.*": "Security Analyst",
    r"pentester.*": "Penetration Tester",
    
    # Management & Product
    r"product manag.*": "Product Manager",
    r"project manag.*": "Project Manager",
    r"scrum.*": "Scrum Master",
    r"tech lead.*": "Tech Lead",
    r"architect.*": "Architect",
    r"director.*": "Director",
    
    # French titles
    r"ing.nieur.*data.*": "Data Engineer",
    r"analyste.*data.*": "Data Analyst",
    r"chef.*projet.*": "Project Manager",
    r"d.veloppeur.*": "Software Developer",
    r"consultant.*data.*": "Data Consultant",
    r"spécialiste.*data.*": "Data Specialist",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SENIORITY LEVEL DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

SENIORITY_MAP = {
    r"junior|débutant|entry level|starter|apprentice|graduate": "Junior",
    r"senior|confirmé|experienced|mid.?level|intermédiaire|\+\s*5": "Senior",
    r"expert|lead|principal|chief|architect|staff|\+\s*10": "Expert",
}

# ═══════════════════════════════════════════════════════════════════════════════
# JOB CATEGORIZATION
# ═══════════════════════════════════════════════════════════════════════════════

JOB_CATEGORIES = {
    r"data|ml|ai|nlp|bi|analyst|scientist": "Data & AI",
    r"devops|cloud|sre|platform|infra": "DevOps & Cloud",
    r"security|cyber|soc|pentest": "Cybersecurity",
    r"software|developer|backend|frontend|full|web|mobile": "Software Dev",
    r"product|project|scrum|manager|lead": "Management",
    r"network|system|linux|admin|it|infrastructure": "IT & Systems",
}

# ═══════════════════════════════════════════════════════════════════════════════
# LOCATION NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

LOCATION_ALIASES = {
    # French regions
    "île-de-france": "Paris",
    "paris": "Paris",
    "ile-de-france": "Paris",
    "paca": "Provence-Alpes-Côte d'Azur",
    "provence": "Provence-Alpes-Côte d'Azur",
    "rhône-alpes": "Auvergne-Rhône-Alpes",
    "nouvelle-aquitaine": "Nouvelle-Aquitaine",
    "occitanie": "Occitanie",
    "hauts-de-france": "Hauts-de-France",
    
    # Remote
    "remote": "Remote",
    "télétravail": "Remote",
    "work from home": "Remote",
    "anywhere": "Remote",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SALARY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SALARY_CONFIG = {
    "CURRENCY": "EUR",
    "MIN_VALID": 20000,      # Minimum valid salary
    "MAX_VALID": 500000,     # Maximum valid salary
    "OUTLIER_PERCENTILE": 99, # Remove salaries above this percentile
}

# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PIPELINE_CONFIG = {
    "BRONZE_TABLE": "jobs",
    "SILVER_TABLE": "silver_jobs",
    "GOLD_TABLES": {
        "snapshots": "gold_daily_jobs_snapshot",
        "companies": "gold_company_stats",
        "locations": "gold_location_stats",
        "titles": "gold_job_title_insights",
        "trends": "gold_monthly_trends",
    },
    "METADATA_TABLE": "medallion_metadata",
    
    # Batch processing
    "BATCH_SIZE": 1000,
    "TIMEOUT_SECONDS": 60,
    "MAX_RETRIES": 3,
    "RETRY_DELAY_SECONDS": 5,
    
    # Data quality
    "MIN_TITLE_LENGTH": 3,
    "MAX_TITLE_LENGTH": 500,
    "MIN_COMPANY_LENGTH": 2,
    "REQUIRED_FIELDS": ["title", "company", "source"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RULES
# ═══════════════════════════════════════════════════════════════════════════════

VALIDATION_RULES = {
    "title": {
        "type": "string",
        "min_length": 3,
        "max_length": 500,
        "required": True,
    },
    "company": {
        "type": "string",
        "min_length": 2,
        "max_length": 200,
        "required": True,
    },
    "location": {
        "type": "string",
        "required": False,
    },
    "salary_min": {
        "type": "numeric",
        "min": 20000,
        "max": 500000,
        "required": False,
    },
    "salary_max": {
        "type": "numeric",
        "min": 20000,
        "max": 500000,
        "required": False,
    },
    "date_posted": {
        "type": "date",
        "required": False,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LOGGING_CONFIG = {
    "FORMAT": "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
    "LEVEL": "INFO",
    "LOG_FILE": "medallion_pipeline.log",
}

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def validate_config() -> Tuple[bool, str]:
    """Validate configuration is properly set"""
    if not SUPABASE_CONFIG["API_KEY"]:
        return False, "SUPABASE_API_KEY not set"
    if not SUPABASE_CONFIG["URL"]:
        return False, "SUPABASE_API_URL not set"
    return True, "Configuration valid"

# Constants for convenience
__all__ = [
    "SUPABASE_CONFIG",
    "get_supabase_headers",
    "SKILLS_LIST",
    "TITLE_MAP",
    "SENIORITY_MAP",
    "JOB_CATEGORIES",
    "LOCATION_ALIASES",
    "SALARY_CONFIG",
    "PIPELINE_CONFIG",
    "VALIDATION_RULES",
    "LOGGING_CONFIG",
    "validate_config",
]
