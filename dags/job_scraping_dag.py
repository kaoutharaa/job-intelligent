"""
Airflow DAG — Projet Job Intelligent (Medallion Architecture)

Daily pipeline:

    extract_linkedin  ──► push_linkedin_bronze  ──► bronze_to_silver_linkedin ──┐
                                                                                  ├──► silver_to_gold
    extract_ft        ──► push_ft_bronze        ──► bronze_to_silver_ft       ──┘

Schedule: every day at 12:00 UTC
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import json
import os
import logging

sys.path.insert(0, "/opt/airflow/scrapers")

from scrapping_linkedin        import scrape_linkedin_jobs
from scrapping_france_travail  import scrape_france_travail_jobs
from db                        import (
    push_linkedin_to_bronze,
    push_ft_to_bronze,
    get_stats,
)
from eda_pipeline import (
    bronze_to_silver_linkedin,
    bronze_to_silver_france_travail,
    silver_to_gold,
)

log = logging.getLogger(__name__)

# ─── DEFAULT ARGS ──────────────────────────────────────────────────────────────

default_args = {
    "owner":          "job_intelligent",
    "retries":        2,
    "retry_delay":    timedelta(minutes=5),
    "email_on_retry": False,
}

# ─── TASK CALLABLES ────────────────────────────────────────────────────────────

def run_extract_linkedin(**context):
    log.info("[DAG] Extracting LinkedIn jobs...")
    jobs = scrape_linkedin_jobs()
    path = "/tmp/linkedin_jobs.json"
    with open(path, "w") as f:
        json.dump(jobs, f)
    log.info(f"[DAG] LinkedIn: {len(jobs)} jobs saved to {path}")


def run_extract_france_travail(**context):
    log.info("[DAG] Extracting France-Travail jobs...")
    jobs = scrape_france_travail_jobs()
    path = "/tmp/ft_jobs.json"
    with open(path, "w") as f:
        json.dump(jobs, f)
    log.info(f"[DAG] France-Travail: {len(jobs)} jobs saved to {path}")


def run_push_linkedin_bronze(**context):
    path = "/tmp/linkedin_jobs.json"
    if not os.path.exists(path):
        log.warning(f"[DAG] {path} not found — skipping bronze push.")
        return
    with open(path) as f:
        jobs = json.load(f)
    log.info(f"[DAG] Pushing {len(jobs)} LinkedIn jobs to bronze...")
    push_linkedin_to_bronze(jobs)


def run_push_ft_bronze(**context):
    path = "/tmp/ft_jobs.json"
    if not os.path.exists(path):
        log.warning(f"[DAG] {path} not found — skipping bronze push.")
        return
    with open(path) as f:
        jobs = json.load(f)
    log.info(f"[DAG] Pushing {len(jobs)} France-Travail jobs to bronze...")
    push_ft_to_bronze(jobs)


def run_bronze_to_silver_linkedin(**context):
    log.info("[DAG] Bronze → Silver: LinkedIn")
    bronze_to_silver_linkedin()


def run_bronze_to_silver_ft(**context):
    log.info("[DAG] Bronze → Silver: France-Travail")
    bronze_to_silver_france_travail()


def run_silver_to_gold(**context):
    log.info("[DAG] Silver → Gold: merging all sources")
    silver_to_gold()
    get_stats()


# ─── DAG DEFINITION ────────────────────────────────────────────────────────────

with DAG(
    dag_id="daily_job_scraping",
    default_args=default_args,
    description="Medallion pipeline: Bronze → Silver → Gold",
    schedule_interval="0 12 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scraping", "medallion", "etl"],
) as dag:

    # ── EXTRACT ────────────────────────────────────────────────────────────────
    extract_linkedin = PythonOperator(
        task_id="extract_linkedin",
        python_callable=run_extract_linkedin,
        execution_timeout=timedelta(minutes=60),
    )

    extract_france_travail = PythonOperator(
        task_id="extract_france_travail",
        python_callable=run_extract_france_travail,
        execution_timeout=timedelta(minutes=10),
    )

    # ── BRONZE ─────────────────────────────────────────────────────────────────
    push_linkedin_bronze = PythonOperator(
        task_id="push_linkedin_bronze",
        python_callable=run_push_linkedin_bronze,
        execution_timeout=timedelta(minutes=10),
    )

    push_ft_bronze = PythonOperator(
        task_id="push_ft_bronze",
        python_callable=run_push_ft_bronze,
        execution_timeout=timedelta(minutes=10),
    )

    # ── SILVER ─────────────────────────────────────────────────────────────────
    silver_linkedin = PythonOperator(
        task_id="bronze_to_silver_linkedin",
        python_callable=run_bronze_to_silver_linkedin,
        execution_timeout=timedelta(minutes=10),
    )

    silver_ft = PythonOperator(
        task_id="bronze_to_silver_france_travail",
        python_callable=run_bronze_to_silver_ft,
        execution_timeout=timedelta(minutes=10),
    )

    # ── GOLD ───────────────────────────────────────────────────────────────────
    gold = PythonOperator(
        task_id="silver_to_gold",
        python_callable=run_silver_to_gold,
        execution_timeout=timedelta(minutes=10),
    )

    # ── PIPELINE FLOW ──────────────────────────────────────────────────────────
    #
    # extract_linkedin  ──► push_linkedin_bronze ──► bronze_to_silver_linkedin ──┐
    #                                                                              ├──► silver_to_gold
    # extract_ft        ──► push_ft_bronze       ──► bronze_to_silver_ft       ──┘
    #

    extract_linkedin       >> push_linkedin_bronze >> silver_linkedin >> gold
    extract_france_travail >> push_ft_bronze       >> silver_ft      >> gold