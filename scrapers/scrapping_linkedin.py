"""
LinkedIn Job Scraper — Projet Job Intelligent
Docker version: connects to Selenium Grid container instead of local chromedriver.

NOTE: This version is configured for the INITIAL DATA LOAD (30 days back).
      After populating the database, change:
        - f_TPR=r2592000  →  f_TPR=r604800   (back to 7 days)
        - MAX_PAGES = 3   →  MAX_PAGES = 2   (back to 2 pages)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import json
import time
import random
import logging
import os
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")

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

    # French variants — important for Morocco market
    "Ingénieur Data",
    "Analyste Data",
    "Développeur",
    "Consultant Data",
]

LOCATION    = "Maroc"
MAX_PAGES   = 3      # 25 jobs per page → up to 75 jobs per keyword (initial load)
MAX_WORKERS = 4      # parallel browser instances

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── BROWSER SETUP ─────────────────────────────────────────────────────────────

def create_driver() -> webdriver.Remote:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def build_url(keyword: str, location: str, start: int = 0) -> str:
    kw  = keyword.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={kw}&location={loc}&start={start}"
        f"&f_TPR=r604800"   # 30 days — change to r604800 for daily runs
    )


def human_delay(min_s=1.5, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


def parse_jobs(html: str, keyword: str) -> list[dict]:
    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="base-card")
    jobs  = []

    for card in cards:
        def txt(sel, attr=None):
            el = card.select_one(sel)
            if not el:
                return ""
            return el.get(attr, "").strip() if attr else el.get_text(strip=True)

        title = txt(".base-search-card__title")
        if not title:
            continue

        url = txt(".base-card__full-link", attr="href")
        jobs.append({
            "title":          title,
            "company":        txt(".base-search-card__subtitle"),
            "location":       txt(".job-search-card__location"),
            "date_posted":    txt("time", attr="datetime"),
            "job_url":        url.split("?")[0] if url else "",
            "search_keyword": keyword,
            "scraped_at":     datetime.utcnow().isoformat(),
            "salary":         "",
            "contract_type":  "",
            "source":         "linkedin",
        })
    return jobs


# ─── PER-KEYWORD SCRAPER ───────────────────────────────────────────────────────

def scrape_keyword(keyword: str) -> list[dict]:
    driver = create_driver()
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    try:
        log.info(f"[LinkedIn][{keyword}] Starting session...")
        driver.get("https://www.linkedin.com/jobs")
        human_delay(2, 4)

        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[contains(text(),'Accept') or contains(text(),'Accepter')]"
            )
            btn.click()
            human_delay(1, 2)
        except Exception:
            pass

        for page in range(MAX_PAGES):
            start = page * 25
            url   = build_url(keyword, LOCATION, start)
            log.info(f"[LinkedIn][{keyword}] Page {page + 1} → {url}")

            driver.get(url)
            human_delay(2, 3)

            for _ in range(4):
                driver.execute_script(
                    "window.scrollBy(0, document.body.scrollHeight / 4);"
                )
                human_delay(0.5, 1.0)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "base-card"))
                )
            except Exception:
                log.warning(f"[LinkedIn][{keyword}] No cards on page {page + 1}, stopping.")
                break

            page_jobs = parse_jobs(driver.page_source, keyword)
            if not page_jobs:
                log.info(f"[LinkedIn][{keyword}] Empty page — stopping.")
                break

            new = [j for j in page_jobs if j["job_url"] not in seen_urls]
            seen_urls.update(j["job_url"] for j in new)
            jobs.extend(new)
            log.info(f"[LinkedIn][{keyword}] +{len(new)} jobs (keyword total: {len(jobs)})")

            human_delay(1.5, 3.0)

    except Exception as e:
        log.error(f"[LinkedIn][{keyword}] Unexpected error: {e}")

    finally:
        driver.quit()
        log.info(f"[LinkedIn][{keyword}] Session closed.")

    return jobs


# ─── PARALLEL ORCHESTRATOR ─────────────────────────────────────────────────────

def scrape_linkedin_jobs() -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str]  = set()

    log.info(
        f"[LinkedIn] Starting {len(KEYWORDS)} keywords "
        f"with {MAX_WORKERS} parallel workers | SELENIUM_URL={SELENIUM_URL}"
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_keyword, kw): kw for kw in KEYWORDS}

        for future in as_completed(futures):
            keyword = futures[future]
            try:
                jobs = future.result()
                new  = [j for j in jobs if j["job_url"] not in seen_urls]
                seen_urls.update(j["job_url"] for j in new)
                all_jobs.extend(new)
                log.info(
                    f"[LinkedIn] Merged '{keyword}' → {len(new)} unique jobs "
                    f"(grand total: {len(all_jobs)})"
                )
            except Exception as e:
                log.error(f"[LinkedIn] Worker failed for '{keyword}': {e}")

    return all_jobs


# ─── SAVE RESULTS (local runs only) ───────────────────────────────────────────

def save_results(jobs: list[dict]) -> None:
    if not jobs:
        log.warning("No jobs collected.")
        return

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    json_path = f"linkedin_jobs_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    log.info(f"Saved → {json_path}")

    csv_path = f"linkedin_jobs_{ts}.csv"
    df = pd.DataFrame(jobs)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info(f"Saved → {csv_path}")

    print("\n─── Summary ─────────────────────────────────────")
    print(f"Total unique jobs : {len(jobs)}")
    print(f"Companies         : {df['company'].nunique()}")
    print(f"\nTop locations:\n{df['location'].value_counts().head(5).to_string()}")
    print(f"\nBy keyword:\n{df['search_keyword'].value_counts().to_string()}")
    print("─────────────────────────────────────────────────\n")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    start_time = datetime.utcnow()
    log.info("=== LinkedIn Job Scraper (INITIAL LOAD — 30 days) ===")
    log.info(f"Keywords: {len(KEYWORDS)} | Workers: {MAX_WORKERS} | Pages: {MAX_PAGES} | Selenium: {SELENIUM_URL}")

    jobs = scrape_linkedin_jobs()
    save_results(jobs)

    elapsed = (datetime.utcnow() - start_time).seconds
    log.info(f"Done in {elapsed // 60}m {elapsed % 60}s — {len(jobs)} unique jobs collected.")