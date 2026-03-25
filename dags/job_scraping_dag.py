"""
Airflow DAG — Projet Job Intelligent
Daily pipeline: extract LinkedIn + France-Travail in parallel → push to PostgreSQL.

Schedule: every day at 12:00 UTC
Graph:
    extract_linkedin       ─┐
                            ├─→ push_to_db → PostgreSQL
    extract_france_travail ─┘
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import json
import os
import logging

sys.path.insert(0, "/opt/airflow/scrapers")

from scrapping_linkedin import scrape_linkedin_jobs
from scrapping_france_travail import scrape_france_travail_jobs
from db import push_to_postgres, get_stats

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
    log.info("[DAG] Starting LinkedIn extraction...")
    jobs = scrape_linkedin_jobs()
    path = "/tmp/linkedin_jobs.json"
    with open(path, "w") as f:
        json.dump(jobs, f)
    log.info(f"[DAG] LinkedIn done — {len(jobs)} jobs saved to {path}")


def run_france_travail(**context):
    log.info("[DAG] Starting France-Travail extraction...")
    jobs = scrape_france_travail_jobs()
    path = "/tmp/france_travail_jobs.json"
    with open(path, "w") as f:
        json.dump(jobs, f)
    log.info(f"[DAG] France-Travail done — {len(jobs)} jobs saved to {path}")


def run_push(**context):
    all_jobs = []

    for path in ["/tmp/linkedin_jobs.json", "/tmp/france_travail_jobs.json"]:
        if os.path.exists(path):
            with open(path) as f:
                jobs = json.load(f)
                all_jobs.extend(jobs)
                log.info(f"[DAG] Loaded {len(jobs)} jobs from {path}")
        else:
            log.warning(f"[DAG] File not found: {path}")

    log.info(f"[DAG] Total jobs to push: {len(all_jobs)}")
    push_to_postgres(all_jobs)
    get_stats()



def run_etl(**context):
    log.info("[DAG] Starting ETL pipeline...")
    sys.path.insert(0, "/opt/airflow/scrapers")
    from EDA import run_pipeline
    run_pipeline()
    log.info("[DAG] ETL done.")

# ─── DAG DEFINITION ────────────────────────────────────────────────────────────

with DAG(
    dag_id="daily_job_scraping",
    default_args=default_args,
    description="Scrape LinkedIn + France-Travail daily and push to PostgreSQL",
    schedule_interval="0 12 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scraping", "jobs", "linkedin", "france_travail"],
) as dag:

    extract_linkedin = PythonOperator(
        task_id="extract_linkedin",
        python_callable=run_linkedin,
        execution_timeout=timedelta(minutes=60),
    )

    extract_france_travail = PythonOperator(
        task_id="extract_france_travail",
        python_callable=run_france_travail,
        execution_timeout=timedelta(minutes=10),
    )

    push_to_db = PythonOperator(
        task_id="push_to_db",
        python_callable=run_push,
        execution_timeout=timedelta(minutes=10),
    )

    run_etl_task = PythonOperator(
    task_id="run_etl",
    python_callable=run_etl,
    execution_timeout=timedelta(minutes=15),
)

    # Both run in parallel → feed into push_to_db
    [extract_linkedin, extract_france_travail] >> push_to_db >>run_etl_task