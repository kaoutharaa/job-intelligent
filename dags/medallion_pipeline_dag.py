"""
Airflow DAG — Medallion Architecture Pipeline
Daily: Bronze → Silver → Gold transformations

Graph:
    extract_linkedin       ┐
    extract_france_travail ├─→ push_to_db (BRONZE) ─→ silver_transform ─→ gold_transform ─→ monitor
                           ┘

Schedule: every day at 12:00 UTC (0 12 * * *)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import json
import os
import logging

sys.path.insert(0, "/opt/airflow")

# Import transformation modules
from scrapers.silver_transformation import transform_bronze_to_silver
from scrapers.gold_transformation import transform_silver_to_gold
from scrapers.scrapping_linkedin import scrape_linkedin_jobs
from scrapers.scrapping_france_travail import scrape_france_travail_jobs
from scrapers.db import push_to_postgres, get_stats
from scrapers.config import PIPELINE_CONFIG

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# DAG CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

default_args = {
    "owner": "medallion_warehouse",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_retry": False,
}

# ═══════════════════════════════════════════════════════════════════════════════
# TASK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_linkedin_task(**context):
    """Extract LinkedIn jobs and save to temporary storage"""
    log.info("[MEDALLION] Extracting LinkedIn jobs...")
    jobs = scrape_linkedin_jobs()
    temp_file = "/tmp/linkedin_jobs.json"
    with open(temp_file, "w") as f:
        json.dump(jobs, f)
    log.info(f"[MEDALLION] LinkedIn extraction complete: {len(jobs)} jobs")
    return len(jobs)

def extract_france_travail_task(**context):
    """Extract France-Travail jobs and save to temporary storage"""
    log.info("[MEDALLION] Extracting France-Travail jobs...")
    jobs = scrape_france_travail_jobs()
    temp_file = "/tmp/france_travail_jobs.json"
    with open(temp_file, "w") as f:
        json.dump(jobs, f)
    log.info(f"[MEDALLION] France-Travail extraction complete: {len(jobs)} jobs")
    return len(jobs)

def push_to_bronze_task(**context):
    """Push raw jobs to BRONZE layer"""
    log.info("[MEDALLION] Pushing to BRONZE layer...")
    all_jobs = []
    
    for source_file in ["/tmp/linkedin_jobs.json", "/tmp/france_travail_jobs.json"]:
        if os.path.exists(source_file):
            with open(source_file) as f:
                jobs = json.load(f)
                all_jobs.extend(jobs)
                log.info(f"[MEDALLION] Loaded {len(jobs)} jobs from {source_file}")
    
    log.info(f"[MEDALLION] Total jobs to push to BRONZE: {len(all_jobs)}")
    push_to_postgres(all_jobs)
    get_stats()

def silver_transform_task(**context):
    """Transform BRONZE → SILVER (cleaning & enrichment)"""
    log.info("[MEDALLION] Starting SILVER transformation...")
    df_silver = transform_bronze_to_silver()
    log.info(f"[MEDALLION] SILVER transformation complete: {len(df_silver)} records")
    return len(df_silver)

def gold_transform_task(**context):
    """Transform SILVER → GOLD (aggregations & insights)"""
    log.info("[MEDALLION] Starting GOLD transformation...")
    results = transform_silver_to_gold()
    log.info(f"[MEDALLION] GOLD transformation complete: {results}")
    return results

def monitor_task(**context):
    """Monitor medallion pipeline execution"""
    log.info("[MEDALLION] ═" * 40)
    log.info("[MEDALLION] Pipeline Execution Complete")
    log.info("[MEDALLION] ═" * 40)
    log.info("[MEDALLION] ✓ Bronze Layer: Raw jobs ingested")
    log.info("[MEDALLION] ✓ Silver Layer: Data cleaned & enriched")
    log.info("[MEDALLION] ✓ Gold Layer: Analytics aggregations complete")
    log.info("[MEDALLION] Ready for BI/Analytics tools")
    log.info("[MEDALLION] ═" * 40)

# ═══════════════════════════════════════════════════════════════════════════════
# DAG DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

with DAG(
    dag_id="medallion_daily_pipeline",
    default_args=default_args,
    description="Medallion architecture: Bronze → Silver → Gold daily ETL",
    schedule="0 12 * * *",  # Daily at 12:00 UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["medallion", "warehouse", "bronze", "silver", "gold"],
) as dag:
    
    # ─────────────────────────────────────────────────────────────────────────
    # EXTRACTION TASKS (run in parallel)
    # ─────────────────────────────────────────────────────────────────────────
    
    extract_linkedin = PythonOperator(
        task_id="extract_linkedin",
        python_callable=extract_linkedin_task,
        execution_timeout=timedelta(minutes=60),
        doc="Extract jobs from LinkedIn",
    )
    
    extract_france_travail = PythonOperator(
        task_id="extract_france_travail",
        python_callable=extract_france_travail_task,
        execution_timeout=timedelta(minutes=60),
        doc="Extract jobs from France-Travail",
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # BRONZE LAYER TASK
    # ─────────────────────────────────────────────────────────────────────────
    
    push_to_bronze = PythonOperator(
        task_id="push_to_bronze",
        python_callable=push_to_bronze_task,
        execution_timeout=timedelta(minutes=30),
        doc="Ingest raw job data into BRONZE layer",
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # SILVER LAYER TASK
    # ─────────────────────────────────────────────────────────────────────────
    
    silver_transform = PythonOperator(
        task_id="silver_transform",
        python_callable=silver_transform_task,
        execution_timeout=timedelta(minutes=60),
        doc="Transform BRONZE → SILVER: clean, normalize, validate, enrich",
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # GOLD LAYER TASK
    # ─────────────────────────────────────────────────────────────────────────
    
    gold_transform = PythonOperator(
        task_id="gold_transform",
        python_callable=gold_transform_task,
        execution_timeout=timedelta(minutes=60),
        doc="Transform SILVER → GOLD: aggregate, compute insights, create dimensions",
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # MONITORING TASK
    # ─────────────────────────────────────────────────────────────────────────
    
    monitor = PythonOperator(
        task_id="monitor_medallion",
        python_callable=monitor_task,
        execution_timeout=timedelta(minutes=5),
        doc="Log pipeline execution summary",
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # TASK DEPENDENCIES
    # ─────────────────────────────────────────────────────────────────────────
    
    [extract_linkedin, extract_france_travail] >> push_to_bronze
    push_to_bronze >> silver_transform
    silver_transform >> gold_transform
    gold_transform >> monitor