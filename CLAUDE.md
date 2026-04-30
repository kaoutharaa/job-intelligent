# CLAUDE.md

This file provides guidance to Claudex when working with code in this repository.

## Run and development commands

### Core stack (Docker Compose)
- **First-time setup / Airflow DB init**:
  `docker compose up airflow-init`
  *(If it exits with code 1, run `docker compose down -v` and try again).*
- **Start full stack** (Postgres, Selenium, API, Airflow webserver/scheduler):
  `docker compose up -d`
- **Rebuild images** (after dependency changes):
  `docker compose build --no-cache`
- **Stop stack** (keep data):
  `docker compose down`
- **Destructive reset** (stop stack & wipe DB volumes):
  `docker compose down -v`
- **View logs**:
  - Scheduler: `docker compose logs -f airflow-scheduler`
  - API: `docker compose logs -f job_api`
  - Postgres: `docker compose logs -f job_postgres`
- **Database debugging**:
  `docker exec -it job_postgres psql -U admin -d job_intelligent`

### Frontend (Vite + React)
- **Install deps**: `cd frontend && npm install`
- **Dev server**: `cd frontend && npm run dev`
- **Lint**: `cd frontend && npm run lint`
- **Build**: `cd frontend && npm run build`

### API (FastAPI)
- **Local run** (without Docker): `uvicorn api.api:app --reload --port 8000`
- **Health check**: `curl http://localhost:8000/health`

### Scrapers / ETL local entry points
- **LinkedIn scraper**: `python scrapers/scrapping_linkedin.py`
- **France-Travail fetcher**: `python scrapers/scrapping_france_travail.py`
- **Full Medallion ETL** (Bronze→Silver→Gold): `python scrapers/eda_pipeline.py`

### Tests
- There is currently no configured automated test suite (`pytest`/`unittest`) in this repo.
- `test.py` is a Fernet key generation helper, not a test runner.

## High-level architecture

### 1) Orchestration layer (Airflow)
- **DAG**: `dags/job_scraping_dag.py` (id: `daily_job_scraping`) runs daily at `12:00 UTC`.
- **Flow**: `extract` -> `push_bronze` -> `bronze_to_silver` (parallel for LinkedIn & France-Travail), then converges to `silver_to_gold`.

### 2) Ingestion layer (Bronze)
- **LinkedIn** (`scrapers/scrapping_linkedin.py`): Scrapes via Selenium Grid (`job_selenium` container).
- **France-Travail** (`scrapers/scrapping_france_travail.py`): Fetches via official API.
- **Persistence** (`scrapers/db.py`): Writes to `bronze_linkedin` / `bronze_france_travail` in local Postgres (`job_postgres`). Uses `ON CONFLICT (job_url) DO NOTHING` for idempotent inserts.
- **Target domain**: The scrapers primarily target data roles (Data Scientist, Data Engineer, NLP Engineer, etc.) in Morocco.

### 3) Transformation layers (Silver + Gold)
- **Pipeline** (`scrapers/eda_pipeline.py`):
  - **Bronze→Silver**: Cleans text fields, standardizes titles, extracts skills, categorizes jobs. Replaces table on each run (`if_exists="replace"`).
  - **Silver→Gold**: Merges all silver tables, globally deduplicates by `job_url`, and replaces `gold_jobs` table. Also exports CSV and JSON to `scrapers/data/`.

### 4) Data model / storage
- **Bootstrap**: `sql/init.sql` (only creates initial tables if provided).
- **Medallion tables**: `bronze_*`, `silver_*`, and `gold_jobs`.
- **Note on users**: `api/api.py` auth endpoints depend on `users` and `user_analyses` tables. If auth fails, verify these schemas exist as they might not be in `init.sql`.

### 5) API layer (`api/api.py`)
- FastApi app sharing the DB connection with Airflow.
- **NLP matching**: `/recommend` endpoint uses `sklearn` `TfidfVectorizer` to match jobs based on title/skills/category against user input (and optionally extracts text from uploaded PDF CVs via `PyPDF2`).
- **Security**: Uses `hashlib.pbkdf2_hmac` with a salt for password hashing (`/register`, `/login`).

### 6) Frontend layer (`frontend/src/`)
- React SPA interacting with `http://localhost:8000`. Features include user auth (localStorage), CV upload for NLP recommendations, and dashboard stats.

## Important implementation notes
- The project recently reverted back to a local Postgres Medallion architecture (from a Supabase migration). Disregard older `README.MD` sections referring to Supabase or `etl_pipeline.py`; the active pipeline uses `eda_pipeline.py` and local PostgreSQL.
- France-Travail API credentials must be injected via `.env` (`FT_CLIENT_ID_api` / `FT_CLIENT_SECRET_api`) which `docker-compose.yaml` maps to container variables.