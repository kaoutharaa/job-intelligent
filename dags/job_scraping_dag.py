"""
Airflow DAG — Projet Job Intelligent
Daily pipeline: extract LinkedIn + Indeed in parallel → push to PostgreSQL.

Schedule: every day at 12:00 UTC
Graph:
    extract_linkedin ─┐
                      ├─→ push_to_db
    extract_indeed   ─┘
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import logging

# Make scrapers importable inside Airflow container
sys.path.insert(0, "/opt/airflow/scrapers")

from scrapping_linkedin import scrape_linkedin_jobs
from scrapping_indeed   import scrape_indeed_jobs
from db                 import push_to_postgres, get_stats

log = logging.getLogger(__name__)

# ─── DAG DEFAULT ARGS ──────────────────────────────────────────────────────────

default_args = {
    "owner":          "job_intelligent",
    "retries":        2,
    "retry_delay":    timedelta(minutes=5),
    "email_on_retry": False,
}

# ─── TASK CALLABLES ────────────────────────────────────────────────────────────

def run_linkedin(**context):
    """
    Task 1a: scrape LinkedIn jobs and push result to XCom
    so push_to_db can retrieve it.
    """
    log.info("[DAG] Starting LinkedIn extraction...")
    jobs = scrape_linkedin_jobs()
    log.info(f"[DAG] LinkedIn done — {len(jobs)} jobs scraped.")
    # XCom stores the result for the downstream push_to_db task
    context["ti"].xcom_push(key="linkedin_jobs", value=jobs)


def run_indeed(**context):
    """
    Task 1b: scrape Indeed jobs and push result to XCom.
    Runs in parallel with run_linkedin.
    """
    log.info("[DAG] Starting Indeed extraction...")
    jobs = scrape_indeed_jobs()
    log.info(f"[DAG] Indeed done — {len(jobs)} jobs scraped.")
    context["ti"].xcom_push(key="indeed_jobs", value=jobs)


def run_push(**context):
    """
    Task 2: pull results from both scrapers via XCom,
    merge them, and push to PostgreSQL.
    """
    ti = context["ti"]

    linkedin_jobs = ti.xcom_pull(key="linkedin_jobs", task_ids="extract_linkedin") or []
    indeed_jobs   = ti.xcom_pull(key="indeed_jobs",   task_ids="extract_indeed")   or []

    all_jobs = linkedin_jobs + indeed_jobs
    log.info(
        f"[DAG] Merging {len(linkedin_jobs)} LinkedIn + "
        f"{len(indeed_jobs)} Indeed = {len(all_jobs)} total jobs."
    )

    push_to_postgres(all_jobs)

    # Print DB stats after insertion
    get_stats()


# ─── DAG DEFINITION ────────────────────────────────────────────────────────────

with DAG(
    dag_id="daily_job_scraping",
    default_args=default_args,
    description="Scrape LinkedIn + Indeed daily and push to PostgreSQL",
    schedule_interval="0 12 * * *",    # every day at 12:00 UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scraping", "jobs", "linkedin", "indeed"],
) as dag:

    extract_linkedin = PythonOperator(
        task_id="extract_linkedin",
        python_callable=run_linkedin,
        execution_timeout=timedelta(minutes=60),
    )

    extract_indeed = PythonOperator(
        task_id="extract_indeed",
        python_callable=run_indeed,
        execution_timeout=timedelta(minutes=60),
    )

    push_to_db = PythonOperator(
        task_id="push_to_db",
        python_callable=run_push,
        execution_timeout=timedelta(minutes=10),
    )

    # LinkedIn and Indeed run in parallel → both feed into push_to_db
    [extract_linkedin, extract_indeed] >> push_to_db