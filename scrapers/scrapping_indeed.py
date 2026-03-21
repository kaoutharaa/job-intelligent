"""
Indeed Job Scraper (ma.indeed.com) — Projet Job Intelligent
Docker version: connects to Selenium Grid container instead of local chromedriver.

Requirements (handled by Docker):
    selenium pandas beautifulsoup4

Local usage (outside Docker):
    pip install selenium pandas beautifulsoup4
    Set SELENIUM_URL=http://localhost:4444/wd/hub
    Run: python scrapping_indeed.py

Notes:
    - Indeed Morocco (ma.indeed.com) is much more scraping-friendly than LinkedIn
    - No login required, cards are server-rendered (no heavy JS wall)
    - Pagination uses &start=0, &start=10, &start=20 (10 jobs per page)
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

# ── DATA-ONLY KEYWORDS (reduced for testing) ───────────────────────────────────
KEYWORDS = [
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Machine Learning Engineer",
    "MLOps Engineer",
    "Business Intelligence",
    "NLP Engineer",
    "AI Engineer",
    "Data Architect",
    "Big Data Engineer",
]

LOCATION    = "Maroc"
MAX_PAGES   = 3        # 10 jobs per page → up to 30 jobs per keyword
MAX_WORKERS = 3        # parallel browser instances

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
    kw  = keyword.replace(" ", "+")
    loc = location.replace(" ", "+")
    return f"https://ma.indeed.com/jobs?q={kw}&l={loc}&start={start}&fromage=30"


def human_delay(min_s=1.5, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


def parse_jobs(html: str, keyword: str) -> list[dict]:
    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="job_seen_beacon")
    jobs  = []

    for card in cards:
        # Title
        title_el = card.select_one("h2.jobTitle span[title]")
        title = title_el.get("title", "").strip() if title_el else ""
        if not title:
            title_el = card.select_one("h2.jobTitle")
            title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        # Company
        company_el = card.select_one("[data-testid='company-name']")
        company = company_el.get_text(strip=True) if company_el else ""

        # Location
        location_el = card.select_one("[data-testid='text-location']")
        location = location_el.get_text(strip=True) if location_el else ""

        # Salary
        salary_el = card.select_one("[data-testid='attribute_snippet_testid']")
        salary = salary_el.get_text(strip=True) if salary_el else ""

        # Contract type
        contract_el = card.select_one(".attribute_snippet")
        contract = contract_el.get_text(strip=True) if contract_el else ""

        # Job URL
        jk_el   = card.select_one("a[data-jk]")
        jk      = jk_el.get("data-jk", "") if jk_el else ""
        job_url = f"https://ma.indeed.com/viewjob?jk={jk}" if jk else ""

        # Date posted
        date_el = card.select_one("span[data-testid='myJobsStateDate']")
        if not date_el:
            date_el = card.select_one(".date")
        date_posted = date_el.get_text(strip=True) if date_el else ""

        jobs.append({
            "title":          title,
            "company":        company,
            "location":       location,
            "date_posted":    date_posted,
            "job_url":        job_url,
            "search_keyword": keyword,
            "scraped_at":     datetime.utcnow().isoformat(),
            "salary":         salary,
            "contract_type":  contract,
            "source":         "indeed",
            "_job_key":       jk,
        })

    return jobs


# ─── PER-KEYWORD SCRAPER ───────────────────────────────────────────────────────

def scrape_keyword(keyword: str) -> list[dict]:
    driver = create_driver()
    jobs: list[dict] = []
    seen_keys: set[str] = set()

    try:
        log.info(f"[Indeed][{keyword}] Starting session...")

        driver.get("https://ma.indeed.com")
        human_delay(2, 3)
        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[contains(@id,'onetrust-accept') "
                "or contains(text(),'Accept') "
                "or contains(text(),'Accepter')]"
            )
            btn.click()
            human_delay(1, 2)
        except Exception:
            pass

        for page in range(MAX_PAGES):
            start = page * 10
            url   = build_url(keyword, LOCATION, start)
            log.info(f"[Indeed][{keyword}] Page {page + 1} → {url}")

            driver.get(url)
            human_delay(2, 3)

            for _ in range(3):
                driver.execute_script(
                    "window.scrollBy(0, document.body.scrollHeight / 3);"
                )
                human_delay(0.5, 1.0)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "job_seen_beacon")
                    )
                )
            except Exception:
                log.warning(f"[Indeed][{keyword}] No cards on page {page + 1}, stopping.")
                break

            page_jobs = parse_jobs(driver.page_source, keyword)
            if not page_jobs:
                log.info(f"[Indeed][{keyword}] Empty page — stopping.")
                break

            new = [j for j in page_jobs if j["_job_key"] not in seen_keys]
            seen_keys.update(j["_job_key"] for j in new)
            jobs.extend(new)
            log.info(f"[Indeed][{keyword}] +{len(new)} jobs (keyword total: {len(jobs)})")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            if soup.select_one(".jobsearch-NoResult"):
                log.info(f"[Indeed][{keyword}] No more results.")
                break

            human_delay(1.5, 3.0)

    except Exception as e:
        log.error(f"[Indeed][{keyword}] Error: {e}")

    finally:
        driver.quit()
        log.info(f"[Indeed][{keyword}] Session closed — {len(jobs)} jobs found.")

    return jobs


# ─── PARALLEL ORCHESTRATOR ─────────────────────────────────────────────────────

def scrape_indeed_jobs() -> list[dict]:
    all_jobs: list[dict] = []
    seen_keys: set[str]  = set()

    log.info(
        f"[Indeed] Starting {len(KEYWORDS)} keywords "
        f"with {MAX_WORKERS} parallel workers | SELENIUM_URL={SELENIUM_URL}"
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_keyword, kw): kw for kw in KEYWORDS}

        for future in as_completed(futures):
            keyword = futures[future]
            try:
                jobs = future.result()
                new = [j for j in jobs if j["_job_key"] not in seen_keys]
                seen_keys.update(j["_job_key"] for j in new)
                all_jobs.extend(new)
                log.info(
                    f"[Indeed] Merged '{keyword}' → {len(new)} unique jobs "
                    f"(grand total: {len(all_jobs)})"
                )
            except Exception as e:
                log.error(f"[Indeed] Worker failed for '{keyword}': {e}")

    # Remove internal dedup key before returning
    for job in all_jobs:
        job.pop("_job_key", None)

    return all_jobs


# ─── SAVE RESULTS (local runs only) ───────────────────────────────────────────

def save_results(jobs: list[dict]) -> None:
    if not jobs:
        log.warning("No jobs collected.")
        return

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    json_path = f"indeed_jobs_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    log.info(f"Saved → {json_path}")

    csv_path = f"indeed_jobs_{ts}.csv"
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
    log.info("=== Indeed Scraper (TEST MODE) — Projet Job Intelligent ===")
    log.info(f"Keywords: {len(KEYWORDS)} | Workers: {MAX_WORKERS} | Pages: {MAX_PAGES} | Selenium: {SELENIUM_URL}")

    jobs = scrape_indeed_jobs()
    save_results(jobs)

    elapsed = (datetime.utcnow() - start_time).seconds
    log.info(f"Done in {elapsed // 60}m {elapsed % 60}s — {len(jobs)} unique jobs collected.")