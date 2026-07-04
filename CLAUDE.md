# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Run and development commands

### Core stack (Docker Compose)
- **First-time Airflow DB init**: `docker compose up airflow-init`
  - If it exits with code 1, run `docker compose down -v` and retry.
- **Start full stack**: `docker compose up -d`
  - Starts PostgreSQL, Selenium Chrome, FastAPI, Airflow webserver, and Airflow scheduler.
- **Rebuild images after dependency changes**: `docker compose build --no-cache`
- **Stop stack and keep data**: `docker compose down`
- **Destructive reset including DB volume**: `docker compose down -v`
- **View logs by Compose service**:
  - Scheduler: `docker compose logs -f airflow-scheduler`
  - API: `docker compose logs -f api`
  - Postgres: `docker compose logs -f postgres`
- **Database shell by container name**: `docker exec -it job_postgres psql -U admin -d job_intelligent`
- **Selenium noVNC**: open `http://localhost:7900` to watch the browser.
- **Airflow UI**: open `http://localhost:8080`, login `admin` / `admin`, DAG id `daily_job_scraping`.

### Frontend (Vite + React)
- **Install deps**: `cd frontend && npm install`
- **Dev server**: `cd frontend && npm run dev`
- **Lint**: `cd frontend && npm run lint`
- **Build**: `cd frontend && npm run build`
- **Preview production build**: `cd frontend && npm run preview`

### Python / API
- **Install Python deps locally**: `pip install -r requirements.txt`
- **Run FastAPI locally**: `uvicorn api.api:app --reload --port 8000`
- **Health check**: `curl http://localhost:8000/health`

### Scrapers / ETL local entry points
- **LinkedIn scraper**: `python scrapers/scrapping_linkedin.py`
- **France-Travail fetcher**: `python scrapers/scrapping_france_travail.py`
- **Full Medallion ETL**: `python scrapers/eda_pipeline.py`

### Tests
- Test suite lives in `tests/` and uses `pytest`. Run all: `python -m pytest tests/ -q`.
- Run a single test: `python -m pytest tests/test_auth.py::test_token_roundtrip -q`.
- `tests/test_auth.py` covers password hashing and JWT token helpers (no DB needed).
- Root `conftest.py` puts the repo root on `sys.path` so `from api.api import ...` resolves.
- `test.py` (repo root) is a Fernet key generation helper, not a test runner.

## High-level architecture

### 1) Orchestration layer (Airflow)
- DAG: `dags/job_scraping_dag.py`, id `daily_job_scraping`, scheduled daily at `12:00 UTC`.
- Pipeline flow:
  - `extract_linkedin -> push_linkedin_bronze -> bronze_to_silver_linkedin`
  - `extract_france_travail -> push_ft_bronze -> bronze_to_silver_france_travail`
  - both silver branches converge into `silver_to_gold`.
- Airflow imports scraper modules from `/opt/airflow/scrapers`; Docker mounts local `./scrapers` there.
- Intermediate extract output is written inside the worker container to `/tmp/linkedin_jobs.json` and `/tmp/ft_jobs.json` before bronze insertion.

### 2) Ingestion / Bronze layer
- LinkedIn ingestion lives in `scrapers/scrapping_linkedin.py` and uses Selenium Grid through the `selenium` service / `job_selenium` container.
- France-Travail ingestion lives in `scrapers/scrapping_france_travail.py` and uses official API credentials from `.env`.
- `scrapers/db.py` writes raw records to `bronze_linkedin` and `bronze_france_travail` in local PostgreSQL.
- Bronze inserts are idempotent by `job_url` with `ON CONFLICT (job_url) DO NOTHING`.
- The active target domain is data/AI and adjacent tech roles, primarily in Morocco.

### 3) Transformation layers (Silver + Gold)
- `scrapers/eda_pipeline.py` is the active ETL pipeline.
- Bronze to Silver:
  - reads each bronze source table separately,
  - cleans text fields,
  - standardizes titles,
  - normalizes locations and dates,
  - extracts skills,
  - categorizes jobs,
  - replaces each silver table on every run.
- Silver to Gold:
  - merges `silver_linkedin` and `silver_france_travail`,
  - globally deduplicates by `job_url`,
  - replaces `gold_jobs`,
  - exports `scrapers/data/gold_jobs.csv` and `scrapers/data/gold_jobs.json`.

### 4) Data model / storage
- `sql/init.sql` bootstraps local PostgreSQL tables for `bronze_*`, `silver_*`, `gold_jobs`, `users`, and `user_analyses`.
- Docker mounts `sql/init.sql` into the Postgres image at startup; schema changes there only apply automatically to new DB volumes.
- The current architecture is local PostgreSQL Medallion storage, not Supabase.

### 5) API layer
- `api/api.py` exposes the local `gold_jobs` table through FastAPI.
- Main endpoints include health checks, job listing/search, stats, recommendations, auth, and saved user analysis history.
- `/recommend` uses `sklearn` TF-IDF/cosine similarity over job title/skills/category and can extract CV text from uploaded PDFs via `PyPDF2`. The TF-IDF corpus is fitted once and cached in-process (`_JobIndex`), rebuilt only when the `gold_jobs` row count changes.
- Auth: `/register` and `/login` return a JWT (`access_token`) plus public user fields; PBKDF2-HMAC hashes passwords in the `users` table. Protected endpoints (`/analysis/me`) derive the user id from the bearer token via the `get_current_user_id` dependency — never from client input. `/recommend` accepts an optional bearer token and only saves history when authenticated.
- Auth env vars: `JWT_SECRET` (required for stable tokens; a random ephemeral secret is used with a warning if unset) and `JWT_EXPIRE_HOURS` (default 24). CORS origins are pinned via `CORS_ORIGINS` (comma-separated; defaults to localhost Vite/CRA ports).

### 6) Frontend layer
- `frontend/src/` is a Vite React SPA.
- `frontend/src/App.jsx` currently contains most UI, state, and API calls.
- The frontend talks to the API at `http://localhost:8000`.
- Current app features include localStorage-backed auth state, CV upload for recommendations, and dashboard/stat views.

## Important implementation notes
- `README.MD` contains older Supabase-oriented sections; treat `CLAUDE.md`, `docker-compose.yaml`, `dags/job_scraping_dag.py`, `scrapers/eda_pipeline.py`, and `sql/init.sql` as the current source of truth.
- France-Travail API credentials must be provided in `.env` as `FT_CLIENT_ID_api` and `FT_CLIENT_SECRET_api`; Docker Compose maps them to `FT_CLIENT_ID` and `FT_CLIENT_SECRET` inside containers.
- Airflow requires `FERNET_KEY` and `SECRET_KEY` in `.env`.
- The API should have `JWT_SECRET` in `.env` (Compose passes it to the `api` service). Without it, tokens use a random per-restart secret and all sessions break on restart. `CORS_ORIGINS` can override the default localhost allowlist.
- Compose service names (`api`, `postgres`, `airflow-scheduler`) differ from container names (`job_api`, `job_postgres`, `job_airflow_scheduler`). Use service names for `docker compose logs` and container names for `docker exec`.
- `requirements.txt` must include any Python library imported by runtime code. `api/api.py` runtime deps beyond the core stack: `PyPDF2` (CV parsing), `PyJWT` (auth tokens), `email-validator` (Pydantic `EmailStr`). `pytest` is included for the test suite.
