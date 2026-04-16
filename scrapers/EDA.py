""""
JobRadar - Pipeline ETL avec Supabase REST API
FIXED VERSION:
  - Extract: lit depuis Supabase `jobs` (plus de CSV locaux)
  - Load:    ecrit dans Supabase `jobs_clean` (table separee)
  - Pas de DELETE sur `jobs` — Airflow continue d'y appender sans conflit
"""

import pandas as pd
import sqlite3
import json
import re
import os
import logging
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
 
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(DATA_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)  # creates scrapers/data automatically

DB_PATH  = os.path.join(OUTPUT_DIR, "jobradar.db")
CSV_OUT  = os.path.join(OUTPUT_DIR, "jobradar_clean.csv")
JSON_OUT = os.path.join(OUTPUT_DIR, "jobradar_clean.json")

load_dotenv()
# ─── SUPABASE CONFIG ─────────────────────────────────────────────────────────
# Set via environment variables — never hardcode secrets in production
SUPABASE_API_URL = os.getenv("SUPABASE_API_URL", "https://egegkouscvcqylndljxp.supabase.co")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "")
# ─────────────────────────────────────────────────────────────────────────────

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
# HELPERS
# =============================================================================

def _check_api_key() -> bool:
    if not SUPABASE_API_KEY:
        log.error("[ETL] SUPABASE_API_KEY manquante ! Definissez-la en variable d'environnement.")
        return False
    return True

def supabase_headers(prefer: str = "return=minimal") -> dict:
    return {
        "apikey":        SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        prefer,
    }

def to_ascii(val) -> str:
    if not isinstance(val, str):
        val = str(val) if val is not None else ""
    return val.encode("ascii", errors="ignore").decode("ascii").replace("\x00", "")

# =============================================================================
# EXTRACT — lit depuis Supabase `jobs` (table raw Airflow)
# =============================================================================

def extract() -> pd.DataFrame:
    """
    Lit tous les jobs depuis la table `jobs` Supabase (insertee par Airflow).
    Pagine par lots de 1000 pour ne pas depasser la limite REST.
    """
    if not _check_api_key():
        return pd.DataFrame()

    log.info("[ETL] Extraction depuis Supabase jobs...")
    all_rows = []
    limit    = 1000
    offset   = 0

    while True:
        resp = requests.get(
            f"{SUPABASE_API_URL}/rest/v1/jobs",
            headers=supabase_headers(prefer="count=exact"),
            params={
                "select": "*",
                "limit":  str(limit),
                "offset": str(offset),
                "order":  "scraped_at.desc",
            },
            timeout=30,
        )

        if resp.status_code not in [200,206]:
            log.error(f"[ETL] Erreur extraction: {resp.status_code} - {resp.text[:300]}")
            break

        batch = resp.json()
        if not batch:
            break

        all_rows.extend(batch)
        log.info(f"[ETL] Page {offset // limit + 1}: {len(all_rows)} lignes recuperees")

        if len(batch) < limit:
            break
        offset += limit

    if not all_rows:
        log.warning("[ETL] Aucune donnee extraite depuis Supabase.")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    log.info(f"[ETL] Extract termine - {len(df)} lignes depuis Supabase `jobs`")
    return df

# =============================================================================
# TRANSFORM
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

def extract_skills(title: str, company: str = "", keyword: str = "") -> str:
    text = f"{title} {company} {keyword}".lower()
    return ", ".join([s for s in SKILLS_LIST if s in text])

def normalize_location(loc: str) -> str:
    if not loc:
        return "Non precise"
    return loc.strip().split(",")[0].strip()

def parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        return pd.to_datetime(date_str).strftime("%Y-%m-%d")
    except Exception:
        return date_str

def categorize(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["data", "ml", "ai", "nlp", "bi ", "analyst"]):
        return "Data & AI"
    if any(x in t for x in ["devops", "cloud", "sre", "platform", "infra"]):
        return "DevOps & Cloud"
    if any(x in t for x in ["security", "cyber", "soc", "pentest"]):
        return "Cybersecurity"
    if any(x in t for x in ["software", "developer", "backend", "frontend", "full"]):
        return "Software Dev"
    if any(x in t for x in ["product", "project", "scrum", "manager"]):
        return "Management"
    if any(x in t for x in ["network", "system", "linux", "admin", "it "]):
        return "IT & Systems"
    return "Other"

def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["title_standard", "company", "location_clean"])
    log.info(f"[ETL] Deduplication: {before} -> {len(df)} lignes ({before - len(df)} supprimees)")
    return df

def transform(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw

    log.info("[ETL] Transformation en cours...")
    df = raw.copy()
    df = df.drop(columns=["salary"], errors="ignore")

    print("salary is deleted")

 

    for col in ["title", "company", "location", "date_posted", "job_url"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)

    df["title_standard"] = df["title"].apply(standardize_title)
    df["location_clean"] = df["location"].apply(normalize_location)
    df["date_clean"]     = df["date_posted"].apply(parse_date)
    df["skills"]         = df.apply(
        lambda r: extract_skills(r["title"], r.get("company", ""),r.get("search_keyword", "")), axis=1
    )
    df["category"] = df["title_standard"].apply(categorize)
    df = deduplicate(df)

    final_cols = [
        "title_standard", "title", "company", "location_clean",
        "date_clean", "category", "skills", "job_url",
        "search_keyword", "scraped_at", "source",
    ]
    df = df[[c for c in final_cols if c in df.columns]]

    rename_map = {
        "title_standard": "title",
        "title":          "title_raw",
        "location_clean": "location",
        "date_clean":     "date_posted",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    log.info(f"[ETL] Transform termine - {len(df)} lignes propres")
    return df

# =============================================================================
# LOAD — ecrit dans Supabase `jobs_clean` (jamais dans `jobs`)
# =============================================================================

def load_to_supabase_clean(df: pd.DataFrame) -> None:
    """
    Remplace le contenu de `jobs_clean` par les donnees transformees.
    Ne touche PAS a la table `jobs` (geree exclusivement par Airflow).
    
    IMPORTANT: Creez la table `jobs_clean` dans Supabase SQL Editor avant
    la premiere execution (voir le schema en bas de ce fichier).
    """
    if not _check_api_key():
        return

    try:
        headers = supabase_headers()

        # Preparer les records
        df_out = df.copy()
        for col in df_out.select_dtypes(include="object").columns:
            df_out[col] = df_out[col].apply(to_ascii)
        df_out = df_out.where(pd.notnull(df_out), None)
        records = df_out.to_dict(orient="records")

        log.info(f"[ETL] Connexion a Supabase REST API (table: jobs_clean)...")

        # Vider jobs_clean (pas jobs !)
        del_resp = requests.delete(
            f"{SUPABASE_API_URL}/rest/v1/jobs_clean",
            headers={**headers, "Prefer": "return=minimal"},
            params={"id": "gte.0"},
            timeout=30,
        )
        if del_resp.status_code in [200, 204]:
            log.info("[ETL] Table jobs_clean videe.")
        else:
            log.warning(f"[ETL] Delete status: {del_resp.status_code} - {del_resp.text[:200]}")

        # Inserer par lots de 100
        chunk_size    = 100
        total_inserted = 0

        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            resp = requests.post(
                f"{SUPABASE_API_URL}/rest/v1/jobs_clean",
                headers=headers,
                json=chunk,
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                total_inserted += len(chunk)
                log.info(f"[ETL] Lot {i // chunk_size + 1}: {total_inserted}/{len(records)} lignes")
            else:
                log.error(f"[ETL] Erreur lot {i // chunk_size + 1}: {resp.status_code} - {resp.text[:300]}")
                break

        log.info(f"[ETL] SUCCES — {total_inserted} lignes dans jobs_clean")

    except Exception as e:
        log.error(f"[ETL] Erreur Supabase: {e}")
        raise

def load_to_sqlite(df: pd.DataFrame) -> None:
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("jobs_clean", conn, if_exists="replace", index=False)
    conn.close()
    log.info(f"[ETL] SQLite backup - {len(df)} lignes -> {DB_PATH}")

def load_to_csv(df: pd.DataFrame) -> None:
    df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
    log.info(f"[ETL] CSV Power BI -> {CSV_OUT}")

def load_to_json(df: pd.DataFrame) -> None:
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    log.info(f"[ETL] JSON NLP -> {JSON_OUT}")

def load(df: pd.DataFrame) -> None:
    if df.empty:
        log.warning("[ETL] Rien a charger.")
        return
    load_to_supabase_clean(df)
    load_to_sqlite(df)
    load_to_csv(df)
    load_to_json(df)

# =============================================================================
# SUMMARY
# =============================================================================

def print_summary(df: pd.DataFrame) -> None:
    if df.empty:
        return
    print("\n--- ETL Summary --------------------------------------------------")
    print(f"Total jobs propres : {len(df)}")
    print(f"Entreprises        : {df['company'].nunique() if 'company' in df.columns else 'N/A'}")
    print(f"Stockage           : Supabase jobs_clean + SQLite backup + CSV + JSON")
    if "category" in df.columns:
        print(f"\nPar categorie:")
        print(df["category"].value_counts().to_string())
    if "location" in df.columns:
        print(f"\nTop localisations:")
        print(df["location"].value_counts().head(5).to_string())
    if "source" in df.columns:
        print(f"\nPar source:")
        print(df["source"].value_counts().to_string())
    print("------------------------------------------------------------------\n")

# =============================================================================
# PIPELINE & SCHEDULER
# =============================================================================

def run_pipeline() -> None:
    log.info("=== JobRadar ETL Pipeline demarre ===")
    start = datetime.now()
    raw   = extract()
    clean = transform(raw)
    load(clean)
    print_summary(clean)
    elapsed = (datetime.now() - start).seconds
    log.info(f"=== Termine en {elapsed}s ===")

def run_scheduled() -> None:
    run_pipeline()
    scheduler = BlockingScheduler()
    # Lance apres le DAG Airflow (12:00 UTC) — laisse 30 min pour le scraping
    scheduler.add_job(run_pipeline, "cron", hour=12, minute=30)
    log.info("[ETL] Scheduler actif - relance chaque jour a 12:30 UTC")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("[ETL] Scheduler arrete.")

if __name__ == "__main__":
    import sys
    scheduled = "--schedule" in sys.argv
    if scheduled:
        run_scheduled()
    else:
        run_pipeline()