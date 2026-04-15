"""
Medallion ETL Pipeline — Projet Job Intelligent

Bronze  → Silver : cleans and enriches each source separately
Silver  → Gold   : merges both sources into one unified table

Called by Airflow DAG tasks:
    - bronze_to_silver_linkedin
    - bronze_to_silver_france_travail
    - silver_to_gold
"""

import pandas as pd
import json
import re
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── DB CONFIG ────────────────────────────────────────────────────────────────

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER', 'admin')}:"
    f"{os.getenv('DB_PASS', 'password')}@"
    f"{os.getenv('DB_HOST', 'postgres')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'job_intelligent')}"
)

# ─── SKILLS & TITLE MAP ──────────────────────────────────────────────────────

SKILLS_LIST = [
    "python", "sql", "spark", "hadoop", "kafka", "airflow", "dbt",
    "power bi", "tableau", "excel", "docker", "kubernetes",
    "aws", "azure", "gcp", "tensorflow", "pytorch", "scikit-learn",
    "pandas", "numpy", "mlflow", "fastapi", "flask", "django",
    "react", "node", "java", "scala", "git", "linux",
    "postgresql", "mongodb", "redis", "elasticsearch",
]

TITLE_MAP = {
    r"data scien.*":       "Data Scientist",
    r"data engin.*":       "Data Engineer",
    r"data analy.*":       "Data Analyst",
    r"machine learn.*":    "ML Engineer",
    r"deep learn.*":       "ML Engineer",
    r"mlops.*":            "MLOps Engineer",
    r"bi anal.*":          "BI Analyst",
    r"business intel.*":   "BI Analyst",
    r"data arch.*":        "Data Architect",
    r"nlp.*":              "NLP Engineer",
    r"computer vision.*":  "Computer Vision Engineer",
    r"ai engin.*":         "AI Engineer",
    r"software engin.*":   "Software Engineer",
    r"backend.*":          "Backend Developer",
    r"frontend.*":         "Frontend Developer",
    r"full.?stack.*":      "Full Stack Developer",
    r"devops.*":           "DevOps Engineer",
    r"cloud engin.*":      "Cloud Engineer",
    r"cybersec.*":         "Cybersecurity Engineer",
    r"security anal.*":    "Security Analyst",
    r"product manag.*":    "Product Manager",
    r"scrum.*":            "Scrum Master",
    r"ing.nieur.*data.*":  "Data Engineer",
    r"analyste.*data.*":   "Data Analyst",
    r"chef.*projet.*":     "Project Manager",
    r"d.veloppeur.*":      "Software Developer",
    r"consultant.*data.*": "Data Consultant",
}

# =============================================================================
# TRANSFORM HELPERS
# =============================================================================

def clean_text(val) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()


def standardize_title(title: str) -> str:
    t = title.lower().strip()
    for pattern, standard in TITLE_MAP.items():
        if re.match(pattern, t):
            return standard
    return title.title()


def extract_skills(title: str, company: str = "") -> str:
    text = f"{title} {company}".lower()
    return ", ".join([s for s in SKILLS_LIST if s in text])


def normalize_location(loc: str) -> str:
    if not loc:
        return "Non précisé"
    return loc.strip().split(",")[0].strip()


def parse_date(date_str: str):
    if not date_str:
        return None
    try:
        return pd.to_datetime(date_str).date()
    except Exception:
        return None


def categorize(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["data", "ml", "ai", "nlp", "bi ", "analyst", "machine"]):
        return "Data & AI"
    if any(x in t for x in ["devops", "cloud", "sre", "platform", "infra", "kubernetes"]):
        return "DevOps & Cloud"
    if any(x in t for x in ["security", "cyber", "soc", "pentest"]):
        return "Cybersecurity"
    if any(x in t for x in ["software", "developer", "backend", "frontend", "full"]):
        return "Software Dev"
    if any(x in t for x in ["product", "project", "scrum", "manager", "chef"]):
        return "Management"
    if any(x in t for x in ["network", "system", "linux", "admin", "it "]):
        return "IT & Systems"
    return "Other"


def transform_bronze(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning and enrichment transformations."""
    if df.empty:
        return df

    for col in ["title", "company", "location", "date_posted", "job_url"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)

    df["title_raw"]  = df["title"]
    df["title"]      = df["title"].apply(standardize_title)
    df["location"]   = df["location"].apply(normalize_location)
    df["date_posted"] = df["date_posted"].apply(parse_date)
    df["skills"]     = df.apply(
        lambda r: extract_skills(r["title_raw"], r.get("company", "")), axis=1
    )
    df["category"]   = df["title"].apply(categorize)

    # Drop duplicates within this batch
    before = len(df)
    df = df.drop_duplicates(subset=["title", "company", "location"])
    log.info(f"[ETL] Dedup: {before} → {len(df)} rows ({before - len(df)} removed)")

    return df

# =============================================================================
# BRONZE → SILVER
# =============================================================================

def _bronze_to_silver(bronze_table: str, silver_table: str) -> None:
    """
    Read from a bronze table, transform, write to its silver table.
    Silver table is fully replaced on each run (fresh clean snapshot).
    """
    engine = create_engine(DB_URL)

    log.info(f"[ETL] Reading from {bronze_table}...")
    df = pd.read_sql(f"SELECT * FROM {bronze_table}", engine)
    log.info(f"[ETL] {len(df)} rows read from {bronze_table}")

    if df.empty:
        log.warning(f"[ETL] {bronze_table} is empty — skipping.")
        return

    # Drop internal bronze columns before transform
    df = df.drop(columns=["id", "ingested_at"], errors="ignore")

    df = transform_bronze(df)

    silver_cols = [
        "title", "title_raw", "company", "location", "date_posted",
        "job_url", "search_keyword", "scraped_at", "salary",
        "contract_type", "skills", "category", "source",
    ]
    df = df[[c for c in silver_cols if c in df.columns]]

    df.to_sql(
        name=silver_table,
        con=engine,
        if_exists="replace",
        index=False,
    )
    log.info(f"[ETL] {len(df)} rows written to {silver_table}")


def bronze_to_silver_linkedin() -> None:
    """Bronze → Silver for LinkedIn data."""
    log.info("[ETL] === Bronze → Silver: LinkedIn ===")
    _bronze_to_silver("bronze_linkedin", "silver_linkedin")


def bronze_to_silver_france_travail() -> None:
    """Bronze → Silver for France-Travail data."""
    log.info("[ETL] === Bronze → Silver: France-Travail ===")
    _bronze_to_silver("bronze_france_travail", "silver_france_travail")

# =============================================================================
# SILVER → GOLD
# =============================================================================

def silver_to_gold() -> None:
    """
    Merge silver_linkedin + silver_france_travail into gold_jobs.
    Gold table is fully replaced on each run.
    Full deduplication by job_url across both sources.
    """
    log.info("[ETL] === Silver → Gold ===")
    engine = create_engine(DB_URL)

    dfs = []
    for table in ["silver_linkedin", "silver_france_travail"]:
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", engine)
            log.info(f"[ETL] Read {len(df)} rows from {table}")
            dfs.append(df)
        except Exception as e:
            log.warning(f"[ETL] Could not read {table}: {e}")

    if not dfs:
        log.warning("[ETL] No silver data found — gold not updated.")
        return

    gold = pd.concat(dfs, ignore_index=True)

    # Drop silver internal columns
    gold = gold.drop(columns=["id", "processed_at"], errors="ignore")

    # Final dedup across all sources by job_url
    before = len(gold)
    gold = gold.drop_duplicates(subset=["job_url"], keep="first")
    log.info(f"[ETL] Gold dedup: {before} → {len(gold)} rows")

    gold_cols = [
        "title", "title_raw", "company", "location", "date_posted",
        "job_url", "search_keyword", "scraped_at", "salary",
        "contract_type", "skills", "category", "source",
    ]
    gold = gold[[c for c in gold_cols if c in gold.columns]]

    gold.to_sql(
        name="gold_jobs",
        con=engine,
        if_exists="replace",
        index=False,
    )
    log.info(f"[ETL] {len(gold)} rows written to gold_jobs")

    # Export for Power BI and NLP
    csv_path  = os.path.join(OUTPUT_DIR, "gold_jobs.csv")
    json_path = os.path.join(OUTPUT_DIR, "gold_jobs.json")
    gold.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            gold.where(pd.notnull(gold), None).to_dict(orient="records"),
            f, ensure_ascii=False, indent=2, default=str
        )
    log.info(f"[ETL] Exported → {csv_path}")
    log.info(f"[ETL] Exported → {json_path}")

    # Summary
    print("\n─── Gold Layer Summary ───────────────────────────────")
    print(f"Total jobs     : {len(gold)}")
    print(f"Companies      : {gold['company'].nunique()}")
    if "source" in gold.columns:
        print(f"\nBy source:\n{gold['source'].value_counts().to_string()}")
    if "category" in gold.columns:
        print(f"\nBy category:\n{gold['category'].value_counts().to_string()}")
    if "location" in gold.columns:
        print(f"\nTop locations:\n{gold['location'].value_counts().head(5).to_string()}")
    print("──────────────────────────────────────────────────────\n")

# =============================================================================
# FULL PIPELINE (for local runs)
# =============================================================================

def run_full_medallion_pipeline() -> None:
    """Run all ETL stages: Bronze→Silver→Gold."""
    log.info("=== Medallion ETL Pipeline started ===")
    start = datetime.now()
    bronze_to_silver_linkedin()
    bronze_to_silver_france_travail()
    silver_to_gold()
    elapsed = (datetime.now() - start).seconds
    log.info(f"=== Medallion ETL Pipeline done in {elapsed}s ===")


if __name__ == "__main__":
    run_full_medallion_pipeline()