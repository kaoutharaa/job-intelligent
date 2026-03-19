"""
JobRadar - Pipeline ETL avec Supabase REST API (HTTP - jamais bloque par firewall)
"""

import pandas as pd
import sqlite3
import json
import re
import os
import glob
import logging
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(DATA_DIR, "jobradar.db")
CSV_OUT  = os.path.join(DATA_DIR, "jobradar_clean.csv")
JSON_OUT = os.path.join(DATA_DIR, "jobradar_clean.json")

# ─── SUPABASE CONFIG ─────────────────────────────────────────────────────────
# Supabase → Settings → API
SUPABASE_API_URL = "https://egegkouscvcqylndljxp.supabase.co"
SUPABASE_API_KEY = "sb_publishable_Q2hyipulXlvHMIZXeUeVbA_Tlv1ANDs"  
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
# EXTRACT
# =============================================================================

def extract() -> pd.DataFrame:
    files = glob.glob(os.path.join(DATA_DIR, "linkedin_jobs_*.csv"))
    if not files:
        log.warning("Aucun fichier CSV trouve.")
        return pd.DataFrame()

    frames = []
    for f in files:
        df = None
        for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(f, encoding=enc)
                break
            except Exception:
                continue
        if df is not None:
            df["source_file"] = os.path.basename(f)
            frames.append(df)
            log.info(f"Charge {len(df)} lignes depuis {os.path.basename(f)}")

    raw = pd.concat(frames, ignore_index=True)
    log.info(f"Extract termine - {len(raw)} lignes depuis {len(files)} fichier(s)")
    return raw

# =============================================================================
# TRANSFORM
# =============================================================================

def clean_text(val) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()

def to_ascii(val) -> str:
    if not isinstance(val, str):
        val = str(val) if val is not None else ""
    return val.encode("ascii", errors="ignore").decode("ascii").replace("\x00", "")

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
    log.info(f"Deduplication: {before} -> {len(df)} lignes ({before - len(df)} supprimees)")
    return df

def transform(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw

    log.info("Transformation en cours...")
    df = raw.copy()

    for col in ["title", "company", "location", "date_posted", "job_url"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)

    df["title_standard"] = df["title"].apply(standardize_title)
    df["location_clean"] = df["location"].apply(normalize_location)
    df["date_clean"]     = df["date_posted"].apply(parse_date)
    df["skills"]         = df.apply(
        lambda r: extract_skills(r["title"], r.get("company", "")), axis=1
    )
    df["category"] = df["title_standard"].apply(categorize)
    df = deduplicate(df)

    final_cols = [
        "title_standard", "title", "company", "location_clean",
        "date_clean", "category", "skills", "job_url",
        "search_keyword", "scraped_at",
    ]
    df = df[[c for c in final_cols if c in df.columns]]
    df.columns = [
        "title", "title_raw", "company", "location",
        "date_posted", "category", "skills", "job_url",
        "search_keyword", "scraped_at",
    ][:len(df.columns)]

    log.info(f"Transform termine - {len(df)} lignes propres")
    return df

# =============================================================================
# LOAD - SUPABASE REST API (HTTP - pas de port PostgreSQL)
# =============================================================================

def supabase_headers() -> dict:
    return {
        "apikey":        SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }

def create_table_via_sql() -> None:
    """Cree la table jobs via l API SQL de Supabase."""
    url = f"{SUPABASE_API_URL}/rest/v1/rpc/exec_sql"
    # La table sera creee automatiquement par upsert
    # Ou via Supabase dashboard → SQL Editor
    pass

def load_to_supabase(df: pd.DataFrame) -> None:
    if not SUPABASE_API_KEY or SUPABASE_API_KEY == "votre_anon_key_ici":
        log.error("SUPABASE_API_KEY manquante ! Allez dans Settings → API → anon public")
        return

    try:
        headers = supabase_headers()

        # Convertir en ASCII et preparer les records
        df_pg = df.copy()
        for col in df_pg.columns:
            df_pg[col] = df_pg[col].apply(to_ascii)

        # Remplacer NaN par None pour JSON
        df_pg = df_pg.where(pd.notnull(df_pg), None)
        records = df_pg.to_dict(orient="records")

        log.info(f"Connexion a Supabase REST API...")

        # Vider la table d'abord
        del_resp = requests.delete(
            f"{SUPABASE_API_URL}/rest/v1/jobs",
            headers={**headers, "Prefer": "return=minimal"},
            params={"id": "gte.0"},
        )
        if del_resp.status_code in [200, 204]:
            log.info("Table jobs videe.")
        else:
            log.warning(f"Delete status: {del_resp.status_code} - {del_resp.text[:200]}")

        # Inserer par lots de 50
        chunk_size = 50
        total_inserted = 0
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            resp = requests.post(
                f"{SUPABASE_API_URL}/rest/v1/jobs",
                headers=headers,
                json=chunk,
            )
            if resp.status_code in [200, 201]:
                total_inserted += len(chunk)
                log.info(f"  Lot {i//chunk_size + 1}: {total_inserted}/{len(records)} lignes")
            else:
                log.error(f"  Erreur lot {i//chunk_size + 1}: {resp.status_code} - {resp.text[:300]}")
                break

        log.info(f"SUCCES Supabase REST - {total_inserted} lignes chargees !")

    except Exception as e:
        log.error(f"Erreur Supabase REST: {e}")
        raise

# =============================================================================
# LOAD - LOCAL
# =============================================================================

def load_to_sqlite(df: pd.DataFrame) -> None:
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("jobs", conn, if_exists="replace", index=False)
    conn.close()
    log.info(f"SQLite backup - {len(df)} lignes -> {DB_PATH}")

def load_to_csv(df: pd.DataFrame) -> None:
    df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
    log.info(f"CSV Power BI -> {CSV_OUT}")

def load_to_json(df: pd.DataFrame) -> None:
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    log.info(f"JSON NLP -> {JSON_OUT}")

def load(df: pd.DataFrame, use_supabase: bool = False) -> None:
    if df.empty:
        log.warning("Rien a charger.")
        return
    if use_supabase:
        load_to_supabase(df)
    load_to_sqlite(df)
    load_to_csv(df)
    load_to_json(df)

# =============================================================================
# SUMMARY
# =============================================================================

def print_summary(df: pd.DataFrame, use_supabase: bool = False) -> None:
    if df.empty:
        return
    storage = "Supabase REST API + SQLite backup" if use_supabase else "SQLite local"
    print("\n--- ETL Summary --------------------------------------------------")
    print(f"Total jobs propres : {len(df)}")
    print(f"Entreprises        : {df['company'].nunique()}")
    print(f"Stockage           : {storage}")
    print(f"\nPar categorie:")
    print(df["category"].value_counts().to_string())
    print(f"\nTop localisations:")
    print(df["location"].value_counts().head(5).to_string())
    print("------------------------------------------------------------------\n")

# =============================================================================
# PIPELINE & SCHEDULER
# =============================================================================

def run_pipeline(use_supabase: bool = False) -> None:
    log.info("=== JobRadar ETL Pipeline demarre ===")
    start = datetime.now()
    raw   = extract()
    clean = transform(raw)
    load(clean, use_supabase=use_supabase)
    print_summary(clean, use_supabase=use_supabase)
    log.info(f"=== Termine en {(datetime.now() - start).seconds}s ===")

def run_scheduled(use_supabase: bool = False) -> None:
    run_pipeline(use_supabase=use_supabase)
    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: run_pipeline(use_supabase), "cron", hour=6, minute=0)
    log.info("Scheduler actif - relance chaque jour a 06:00")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler arrete.")

if __name__ == "__main__":
    import sys
    use_supabase = "--supabase" in sys.argv
    scheduled    = "--schedule" in sys.argv
    if scheduled:
        run_scheduled(use_supabase=use_supabase)
    else:
        run_pipeline(use_supabase=use_supabase)