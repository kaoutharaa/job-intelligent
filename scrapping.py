# """
# LinkedIn Job Scraper — Projet Job Intelligent
# Fixed version: uses manual chromedriver path (no webdriver-manager win32 bug).

# Requirements:
#     pip install selenium pandas beautifulsoup4

# Setup:
#     1. Download chromedriver win64 from:
#        https://storage.googleapis.com/chrome-for-testing-public/146.0.7680.80/win64/chromedriver-win64.zip
#     2. Extract → copy chromedriver.exe → paste in same folder as this script
#     3. Run: python scrapping.py
# """

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
# import pandas as pd
# import json
# import time
# import random
# import logging
# import os
# from datetime import datetime

# # ─── CONFIG ────────────────────────────────────────────────────────────────────

# # Path to chromedriver.exe — place it in the same folder as this script
# CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")

# KEYWORDS = [
#     # 🔹 Data & AI
#     "Data Scientist",
#     "Data Engineer",
#     "Data Analyst",
#     "Machine Learning Engineer",
#     "Deep Learning Engineer",
#     "AI Engineer",
#     "NLP Engineer",
#     "Computer Vision Engineer",
#     "MLOps Engineer",
#     "Business Intelligence",
#     "BI Analyst",
#     "Data Architect",

#     # 🔹 Software Development
#     "Software Engineer",
#     "Software Developer",
#     "Backend Developer",
#     "Frontend Developer",
#     "Full Stack Developer",
#     "Web Developer",
#     "Mobile Developer",
#     "Android Developer",
#     "iOS Developer",

#     # 🔹 DevOps & Cloud
#     "DevOps Engineer",
#     "Cloud Engineer",
#     "Cloud Architect",
#     "Site Reliability Engineer",
#     "Platform Engineer",
#     "Infrastructure Engineer",
#     "Kubernetes Engineer",

#     # 🔹 Cybersecurity
#     "Cybersecurity Engineer",
#     "Security Analyst",
#     "Penetration Tester",
#     "Ethical Hacker",
#     "SOC Analyst",
#     "Information Security",

#     # 🔹 Networking & Systems
#     "Network Engineer",
#     "System Administrator",
#     "Linux Administrator",
#     "IT Support",
#     "System Engineer",

#     # 🔹 Database
#     "Database Administrator",
#     "SQL Developer",
#     "Data Architect",
#     "Big Data Engineer",

#     # 🔹 QA & Testing
#     "QA Engineer",
#     "Test Engineer",
#     "Automation Tester",
#     "Software Tester",

#     # 🔹 UI/UX & Design
#     "UI Designer",
#     "UX Designer",
#     "Product Designer",

#     # 🔹 Product & Management
#     "Product Manager",
#     "Project Manager",
#     "Scrum Master",
#     "Technical Lead",
#     "Engineering Manager",

#     # 🔹 Embedded & Hardware
#     "Embedded Systems Engineer",
#     "IoT Engineer",
#     "Hardware Engineer",
#     "Robotics Engineer",

#     # 🔹 Game Dev
#     "Game Developer",
#     "Game Designer",
#     "Unity Developer",
#     "Unreal Engine Developer",

#     # 🔹 Blockchain & New Tech
#     "Blockchain Developer",
#     "Web3 Developer",
#     "AR/VR Developer",

#     # 🔹 General IT
#     "IT Engineer",
#     "IT Consultant",
#     "Tech Lead",
# ]
# LOCATION  = "France"
# MAX_PAGES = 3      # 25 jobs per page
# HEADLESS  = False  # set True to run without visible browser window

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )
# log = logging.getLogger(__name__)

# # ─── BROWSER SETUP ─────────────────────────────────────────────────────────────

# def create_driver() -> webdriver.Chrome:
#     """Create a Chrome driver using local chromedriver.exe."""

#     # Verify chromedriver exists
#     if not os.path.exists(CHROMEDRIVER_PATH):
#         raise FileNotFoundError(
#             f"\n\n chromedriver.exe not found at: {CHROMEDRIVER_PATH}\n"
#             f" Download it from:\n"
#             f" https://storage.googleapis.com/chrome-for-testing-public/"
#             f"146.0.7680.80/win64/chromedriver-win64.zip\n"
#             f" Extract and place chromedriver.exe next to this script.\n"
#         )

#     options = Options()

#     if HEADLESS:
#         options.add_argument("--headless=new")

#     # Anti-detection
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option("useAutomationExtension", False)
#     options.add_argument("--window-size=1280,900")
#     options.add_argument(
#         "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/146.0.0.0 Safari/537.36"
#     )

#     service = Service(executable_path=CHROMEDRIVER_PATH)
#     driver  = webdriver.Chrome(service=service, options=options)

#     # Remove webdriver JS flag
#     driver.execute_script(
#         "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
#     )
#     log.info("Browser started successfully.")
#     return driver


# # ─── HELPERS ───────────────────────────────────────────────────────────────────

# def build_url(keyword: str, location: str, start: int = 0) -> str:
#     kw  = keyword.replace(" ", "%20")
#     loc = location.replace(" ", "%20")
#     return (
#         f"https://www.linkedin.com/jobs/search/"
#         f"?keywords={kw}&location={loc}&start={start}&f_TPR=r604800"
#     )


# def human_delay(min_s=2.0, max_s=4.5):
#     time.sleep(random.uniform(min_s, max_s))


# def parse_jobs(html: str, keyword: str) -> list[dict]:
#     soup  = BeautifulSoup(html, "html.parser")
#     cards = soup.find_all("div", class_="base-card")
#     jobs  = []

#     for card in cards:
#         def txt(sel, attr=None):
#             el = card.select_one(sel)
#             if not el:
#                 return ""
#             return el.get(attr, "").strip() if attr else el.get_text(strip=True)

#         title = txt(".base-search-card__title")
#         if not title:
#             continue

#         url = txt(".base-card__full-link", attr="href")
#         jobs.append({
#             "title":           title,
#             "company":         txt(".base-search-card__subtitle"),
#             "location":        txt(".job-search-card__location"),
#             "date_posted":     txt("time", attr="datetime"),
#             "job_url":         url.split("?")[0] if url else "",
#             "search_keyword":  keyword,
#             "scraped_at":      datetime.utcnow().isoformat(),
#         })
#     return jobs


# # ─── MAIN SCRAPER ──────────────────────────────────────────────────────────────

# def scrape_linkedin_jobs() -> list[dict]:
#     driver    = create_driver()
#     all_jobs  = []
#     seen_urls: set[str] = set()

#     try:
#         log.info("Opening LinkedIn...")
#         driver.get("https://www.linkedin.com/jobs")
#         human_delay(3, 5)

#         # Accept cookies if banner appears
#         try:
#             btn = driver.find_element(
#                 By.XPATH,
#                 "//button[contains(text(),'Accept') or contains(text(),'Accepter')]"
#             )
#             btn.click()
#             human_delay(1, 2)
#         except Exception:
#             pass

#         for keyword in KEYWORDS:
#             log.info(f"Searching: '{keyword}' in '{LOCATION}'")

#             for page in range(MAX_PAGES):
#                 start = page * 25
#                 url   = build_url(keyword, LOCATION, start)
#                 log.info(f"  Page {page + 1} → {url}")

#                 driver.get(url)
#                 human_delay(3, 5)

#                 # Scroll to load all cards
#                 for _ in range(4):
#                     driver.execute_script(
#                         "window.scrollBy(0, document.body.scrollHeight / 4);"
#                     )
#                     human_delay(0.8, 1.5)

#                 # Wait for cards
#                 try:
#                     WebDriverWait(driver, 10).until(
#                         EC.presence_of_element_located((By.CLASS_NAME, "base-card"))
#                     )
#                 except Exception:
#                     log.warning(f"  No cards on page {page + 1}, stopping.")
#                     break

#                 jobs = parse_jobs(driver.page_source, keyword)
#                 if not jobs:
#                     log.info(f"  Empty page — stopping '{keyword}'.")
#                     break

#                 new = [j for j in jobs if j["job_url"] not in seen_urls]
#                 seen_urls.update(j["job_url"] for j in new)
#                 all_jobs.extend(new)
#                 log.info(f"  +{len(new)} jobs (total: {len(all_jobs)})")

#                 human_delay(2, 4)

#     finally:
#         driver.quit()
#         log.info("Browser closed.")

#     return all_jobs


# # ─── SAVE RESULTS ──────────────────────────────────────────────────────────────

# def save_results(jobs: list[dict]) -> None:
#     if not jobs:
#         log.warning("No jobs collected.")
#         return

#     ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

#     json_path = f"linkedin_jobs_{ts}.json"
#     with open(json_path, "w", encoding="utf-8") as f:
#         json.dump(jobs, f, ensure_ascii=False, indent=2)
#     log.info(f"Saved → {json_path}")

#     csv_path = f"linkedin_jobs_{ts}.csv"
#     df = pd.DataFrame(jobs)
#     df.to_csv(csv_path, index=False, encoding="utf-8-sig")
#     log.info(f"Saved → {csv_path}")

#     print("\n─── Summary ─────────────────────────────────────")
#     print(f"Total jobs     : {len(jobs)}")
#     print(f"Companies      : {df['company'].nunique()}")
#     print(f"\nTop locations:\n{df['location'].value_counts().head(5).to_string()}")
#     print(f"\nBy keyword:\n{df['search_keyword'].value_counts().to_string()}")
#     print("─────────────────────────────────────────────────\n")


# # ─── ENTRY POINT ───────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     log.info("=== LinkedIn Job Scraper (Selenium) — Projet Job Intelligent ===")
#     jobs = scrape_linkedin_jobs()
#     save_results(jobs)
#     log.info("Done.")










"""
LinkedIn Job Scraper — Projet Job Intelligent
Fixed version: uses manual chromedriver path (no webdriver-manager win32 bug).

Requirements:
    pip install selenium pandas beautifulsoup4

Setup:
    1. Download chromedriver win64 from:
       https://storage.googleapis.com/chrome-for-testing-public/146.0.7680.80/win64/chromedriver-win64.zip
    2. Extract → copy chromedriver.exe → paste in same folder as this script
    3. Run: python scrapping.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
import logging
import os
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────────

# Path to chromedriver.exe — place it in the same folder as this script
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")

KEYWORDS = [
    # Data & AI
    "Data Scientist", "Data Engineer", "Data Analyst",
    "Machine Learning Engineer", "Deep Learning Engineer", "AI Engineer",
    "NLP Engineer", "Computer Vision Engineer", "MLOps Engineer",
    "Business Intelligence", "BI Analyst", "Data Architect",

    # Software Development
    "Software Engineer", "Software Developer", "Backend Developer",
    "Frontend Developer", "Full Stack Developer", "Web Developer",
    "Mobile Developer", "Android Developer", "iOS Developer",

    # DevOps & Cloud
    "DevOps Engineer", "Cloud Engineer", "Cloud Architect",
    "Site Reliability Engineer", "Platform Engineer",
    "Infrastructure Engineer", "Kubernetes Engineer",

    # Cybersecurity
    "Cybersecurity Engineer", "Security Analyst", "Penetration Tester",
    "Ethical Hacker", "SOC Analyst", "Information Security",

    # Networking & Systems
    "Network Engineer", "System Administrator", "Linux Administrator",
    "IT Support", "System Engineer",

    # Database
    "Database Administrator", "SQL Developer", "Big Data Engineer",

    # QA & Testing
    "QA Engineer", "Test Engineer", "Automation Tester", "Software Tester",

    # UI/UX & Design
    "UI Designer", "UX Designer", "Product Designer",

    # Product & Management
    "Product Manager", "Project Manager", "Scrum Master",
    "Technical Lead", "Engineering Manager",

    # Embedded & Hardware
    "Embedded Systems Engineer", "IoT Engineer",
    "Hardware Engineer", "Robotics Engineer",

    # Game Dev
    "Game Developer", "Game Designer", "Unity Developer",
    "Unreal Engine Developer",

    # Blockchain & New Tech
    "Blockchain Developer", "Web3 Developer", "AR/VR Developer",

    # General IT
    "IT Engineer", "IT Consultant", "Tech Lead",
]

# Estimated run time: ~75 keywords x 3 pages x ~12s = ~45 minutes
# Set MAX_PAGES = 1 for a quick test (~15 min)
LOCATION  = "Maroc"
MAX_PAGES = 3      # 25 jobs per page
HEADLESS  = False  # set True to hide browser window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── BROWSER SETUP ─────────────────────────────────────────────────────────────

def create_driver() -> webdriver.Chrome:
    """Create a Chrome driver using local chromedriver.exe."""

    # Verify chromedriver exists
    if not os.path.exists(CHROMEDRIVER_PATH):
        raise FileNotFoundError(
            f"\n\n chromedriver.exe not found at: {CHROMEDRIVER_PATH}\n"
            f" Download it from:\n"
            f" https://storage.googleapis.com/chrome-for-testing-public/"
            f"146.0.7680.80/win64/chromedriver-win64.zip\n"
            f" Extract and place chromedriver.exe next to this script.\n"
        )

    options = Options()

    if HEADLESS:
        options.add_argument("--headless=new")

    # Anti-detection
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver  = webdriver.Chrome(service=service, options=options)

    # Remove webdriver JS flag
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    log.info("Browser started successfully.")
    return driver


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def build_url(keyword: str, location: str, start: int = 0) -> str:
    kw  = keyword.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={kw}&location={loc}&start={start}&f_TPR=r604800"
    )


def human_delay(min_s=2.0, max_s=4.5):
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
            "title":           title,
            "company":         txt(".base-search-card__subtitle"),
            "location":        txt(".job-search-card__location"),
            "date_posted":     txt("time", attr="datetime"),
            "job_url":         url.split("?")[0] if url else "",
            "search_keyword":  keyword,
            "scraped_at":      datetime.utcnow().isoformat(),
        })
    return jobs


# ─── MAIN SCRAPER ──────────────────────────────────────────────────────────────

def scrape_linkedin_jobs() -> list[dict]:
    driver    = create_driver()
    all_jobs  = []
    seen_urls: set[str] = set()

    try:
        log.info("Opening LinkedIn...")
        driver.get("https://www.linkedin.com/jobs")
        human_delay(3, 5)

        # Accept cookies if banner appears
        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[contains(text(),'Accept') or contains(text(),'Accepter')]"
            )
            btn.click()
            human_delay(1, 2)
        except Exception:
            pass

        for keyword in KEYWORDS:
            log.info(f"Searching: '{keyword}' in '{LOCATION}'")

            for page in range(MAX_PAGES):
                start = page * 25
                url   = build_url(keyword, LOCATION, start)
                log.info(f"  Page {page + 1} → {url}")

                driver.get(url)
                human_delay(3, 5)

                # Scroll to load all cards
                for _ in range(4):
                    driver.execute_script(
                        "window.scrollBy(0, document.body.scrollHeight / 4);"
                    )
                    human_delay(0.8, 1.5)

                # Wait for cards
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "base-card"))
                    )
                except Exception:
                    log.warning(f"  No cards on page {page + 1}, stopping.")
                    break

                jobs = parse_jobs(driver.page_source, keyword)
                if not jobs:
                    log.info(f"  Empty page — stopping '{keyword}'.")
                    break

                new = [j for j in jobs if j["job_url"] not in seen_urls]
                seen_urls.update(j["job_url"] for j in new)
                all_jobs.extend(new)
                log.info(f"  +{len(new)} jobs (total: {len(all_jobs)})")

                human_delay(2, 4)

    finally:
        driver.quit()
        log.info("Browser closed.")

    return all_jobs


# ─── SAVE RESULTS ──────────────────────────────────────────────────────────────

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
    print(f"Total jobs     : {len(jobs)}")
    print(f"Companies      : {df['company'].nunique()}")
    print(f"\nTop locations:\n{df['location'].value_counts().head(5).to_string()}")
    print(f"\nBy keyword:\n{df['search_keyword'].value_counts().to_string()}")
    print("─────────────────────────────────────────────────\n")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=== LinkedIn Job Scraper (Selenium) — Projet Job Intelligent ===")
    jobs = scrape_linkedin_jobs()
    save_results(jobs)
    log.info("Done.")