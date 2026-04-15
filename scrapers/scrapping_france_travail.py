"""
France-Travail API Scraper — Projet Job Intelligent
Uses the official France-Travail (Pôle Emploi) API — no scraping, no blocks.

NOTE: This version is configured for the INITIAL DATA LOAD (31 days back).
      After populating the database, change:
        - publieeDepuis: 31  →  publieeDepuis: 7   (back to 7 days)
        - MAX_PAGES = 3      →  MAX_PAGES = 2      (back to 2 pages)
"""

import os
import time
import logging
import requests
import pandas as pd
import json
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────────

FT_CLIENT_ID     = os.getenv("FT_CLIENT_ID", "")
FT_CLIENT_SECRET = os.getenv("FT_CLIENT_SECRET", "")

TOKEN_URL  = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

# ── EXPANDED KEYWORDS matching TITLE_MAP from ETL pipeline ────────────────────
KEYWORDS = [
    # Data & AI
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Machine Learning Engineer",
    "Deep Learning Engineer",
    "MLOps Engineer",
    "BI Analyst",
    "Business Intelligence",
    "Data Architect",
    "NLP Engineer",
    "Computer Vision Engineer",
    "AI Engineer",

    # Software Development
    "Software Engineer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    "Software Developer",

    # DevOps & Cloud
    "DevOps Engineer",
    "Cloud Engineer",

    # Cybersecurity
    "Cybersecurity Engineer",
    "Security Analyst",

    # Management
    "Product Manager",
    "Scrum Master",
    "Chef de projet",

    # French variants — important for Morocco/France market
    "Ingénieur Data",
    "Analyste Data",
    "Développeur",
    "Consultant Data",
]

RESULTS_PER_PAGE = 50   # max per API call
MAX_PAGES        = 3    # up to 150 results per keyword (initial load)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── AUTH ──────────────────────────────────────────────────────────────────────

_token_cache = {"token": None, "expires_at": 0}

def get_token() -> str:
    """
    Get OAuth2 access token from France-Travail.
    Token is cached and refreshed automatically when it expires (1500s lifetime).
    """
    now = time.time()

    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    log.info("[FranceTravail] Refreshing access token...")

    response = requests.post(
        TOKEN_URL,
        params={"realm": "/partenaire"},
        data={
            "grant_type":    "client_credentials",
            "client_id":     FT_CLIENT_ID,
            "client_secret": FT_CLIENT_SECRET,
            "scope":         "api_offresdemploiv2 o2dsoffre",
        },
        timeout=15,
    )

    if response.status_code != 200:
        raise Exception(
            f"[FranceTravail] Token error {response.status_code}: {response.text}"
        )

    data = response.json()
    _token_cache["token"]      = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 1500)

    log.info("[FranceTravail] Token obtained successfully.")
    return _token_cache["token"]


# ─── SEARCH ────────────────────────────────────────────────────────────────────

def search_jobs(keyword: str, start: int = 0) -> list[dict]:
    """
    Search for job offers using France-Travail API.
    Returns a list of normalized job dicts matching the unified schema.
    """
    token = get_token()
    end   = start + RESULTS_PER_PAGE - 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }

    params = {
        "motsCles":      keyword,
        "range":         f"{start}-{end}",
        "sort":          "1",    # most recent first
        "publieeDepuis": 7,     # last 31 days — change to 7 for daily runs
    }

    try:
        response = requests.get(
            SEARCH_URL,
            headers=headers,
            params=params,
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        log.error(f"[FranceTravail][{keyword}] Request error: {e}")
        return []

    if response.status_code == 204:
        log.info(f"[FranceTravail][{keyword}] No results (204).")
        return []

    if response.status_code != 200:
        log.warning(
            f"[FranceTravail][{keyword}] Error {response.status_code}: {response.text[:200]}"
        )
        return []

    data    = response.json()
    results = data.get("resultats", [])
    jobs    = []

    for item in results:
        # Salary
        salary = ""
        if "salaire" in item and item["salaire"]:
            salary = item["salaire"].get("libelle", "")

        # Location
        location = ""
        if "lieuTravail" in item:
            location = item["lieuTravail"].get("libelle", "")

        # Contract type
        contract_type = item.get("typeContratLibelle", "")

        # Job URL
        job_id  = item.get("id", "")
        job_url = (
            f"https://candidat.francetravail.fr/offres/recherche/detail/{job_id}"
            if job_id else ""
        )

        jobs.append({
            "title":          item.get("intitule", ""),
            "company":        item.get("entreprise", {}).get("nom", ""),
            "location":       location,
            "date_posted":    item.get("dateCreation", ""),
            "job_url":        job_url,
            "search_keyword": keyword,
            "scraped_at":     datetime.utcnow().isoformat(),
            "salary":         salary,
            "contract_type":  contract_type,
            "source":         "france_travail",
        })

    return jobs


# ─── MAIN SCRAPER ──────────────────────────────────────────────────────────────

def scrape_france_travail_jobs() -> list[dict]:
    """
    Fetch jobs for all keywords from France-Travail API.
    Called by Airflow DAG task: extract_france_travail.
    """
    if not FT_CLIENT_ID or not FT_CLIENT_SECRET:
        raise Exception(
            "[FranceTravail] FT_CLIENT_ID and FT_CLIENT_SECRET env vars are not set. "
            "Add them to docker-compose.yml."
        )

    all_jobs: list[dict] = []
    seen_urls: set[str]  = set()

    log.info(f"[FranceTravail] Starting {len(KEYWORDS)} keywords (31 days back)...")

    for keyword in KEYWORDS:
        log.info(f"[FranceTravail] Searching: '{keyword}'")
        keyword_jobs = []

        for page in range(MAX_PAGES):
            start = page * RESULTS_PER_PAGE
            jobs  = search_jobs(keyword, start)

            if not jobs:
                log.info(f"[FranceTravail][{keyword}] No more results at page {page + 1}.")
                break

            new = [j for j in jobs if j["job_url"] not in seen_urls]
            seen_urls.update(j["job_url"] for j in new)
            keyword_jobs.extend(new)
            log.info(
                f"[FranceTravail][{keyword}] Page {page + 1} → "
                f"+{len(new)} jobs (keyword total: {len(keyword_jobs)})"
            )

            time.sleep(0.5)  # respect API rate limits

        all_jobs.extend(keyword_jobs)
        log.info(
            f"[FranceTravail] '{keyword}' done → "
            f"{len(keyword_jobs)} jobs (grand total: {len(all_jobs)})"
        )

        time.sleep(1)  # small delay between keywords

    log.info(f"[FranceTravail] Finished — {len(all_jobs)} unique jobs collected.")
    return all_jobs


# ─── SAVE RESULTS (local runs only) ───────────────────────────────────────────

def save_results(jobs: list[dict]) -> None:
    if not jobs:
        log.warning("No jobs collected.")
        return

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    json_path = f"ft_jobs_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    log.info(f"Saved → {json_path}")

    csv_path = f"ft_jobs_{ts}.csv"
    df = pd.DataFrame(jobs)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info(f"Saved → {csv_path}")

    print("\n─── Summary ──────────────────────────────────────")
    print(f"Total unique jobs : {len(jobs)}")
    print(f"Companies         : {df['company'].nunique()}")
    print(f"\nTop locations:\n{df['location'].value_counts().head(5).to_string()}")
    print(f"\nBy keyword:\n{df['search_keyword'].value_counts().to_string()}")
    if "contract_type" in df.columns and df["contract_type"].any():
        print(f"\nBy contract:\n{df['contract_type'].value_counts().head(5).to_string()}")
    print("──────────────────────────────────────────────────\n")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    start_time = datetime.utcnow()
    log.info("=== France-Travail API Scraper (INITIAL LOAD — 31 days) ===")
    log.info(f"Keywords: {len(KEYWORDS)} | Pages: {MAX_PAGES} | Results/page: {RESULTS_PER_PAGE}")

    jobs = scrape_france_travail_jobs()
    save_results(jobs)

    elapsed = (datetime.utcnow() - start_time).seconds
    log.info(f"Done in {elapsed // 60}m {elapsed % 60}s — {len(jobs)} unique jobs collected.")