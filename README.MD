# Job Intelligent

A full-stack job-market intelligence platform for **data & AI roles in Morocco**. It scrapes job listings from **LinkedIn** and the **France-Travail API**, refines them through a **Medallion (Bronze → Silver → Gold) ETL pipeline** in PostgreSQL, and serves them through a **FastAPI** backend and a **React** frontend featuring CV-based job recommendations.

Everything is orchestrated by **Apache Airflow** and runs in **Docker Compose**.

---

## Architecture

```
                     ┌─────────────────────── Airflow DAG: daily_job_scraping ───────────────────────┐
                     │                                                                                │
 LinkedIn (Selenium) │  extract_linkedin ─► push_linkedin_bronze ─► bronze_to_silver_linkedin ──┐    │
                     │                                                                            ├─► silver_to_gold
 France-Travail (API)│  extract_ft       ─► push_ft_bronze       ─► bronze_to_silver_ft       ──┘    │
                     └────────────────────────────────────────────────────────────────────────────────┘
                                                          │
                                     PostgreSQL (Medallion layers)
                                     bronze_* → silver_* → gold_jobs
                                                          │
                                        FastAPI  ◄────────┘  ──►  React SPA (Vite)
                                     (jobs, stats, auth, /recommend)
```

**Medallion layers**
- **Bronze** — raw scraped records, one table per source, idempotent by `job_url`.
- **Silver** — cleaned & standardized (titles, locations, dates, extracted skills, categories), one table per source.
- **Gold** — `gold_jobs`: unified, globally deduplicated, fully indexed for search, stats, and NLP.

---

## Tech stack

| Layer | Tool |
|-------|------|
| Orchestration | Apache Airflow (LocalExecutor) |
| Scraping | Selenium Grid (Chrome) + BeautifulSoup4 |
| Ingestion | France-Travail REST API |
| Storage | PostgreSQL 15 (Medallion) |
| ETL | Python (pandas) |
| API | FastAPI + SQLAlchemy |
| Recommendations | scikit-learn (TF-IDF + cosine similarity), PyPDF2 (CV parsing) |
| Auth | JWT (PyJWT) + PBKDF2-HMAC password hashing |
| Frontend | React + Vite |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 |

---

## Repository layout

```
job-intelligent/
├── dags/
│   └── job_scraping_dag.py          # Airflow DAG (daily @ 12:00 UTC)
├── scrapers/
│   ├── scrapping_linkedin.py        # LinkedIn scraper (Selenium)
│   ├── scrapping_france_travail.py  # France-Travail API fetcher
│   ├── db.py                        # Bronze-layer insert helpers
│   └── eda_pipeline.py              # Bronze → Silver → Gold ETL
├── api/
│   └── api.py                       # FastAPI app (jobs, stats, auth, recommend)
├── frontend/                        # React + Vite SPA
├── sql/
│   └── init.sql                     # Bootstraps all Postgres tables
├── tests/
│   └── test_auth.py                 # Password hashing + JWT unit tests
├── docker-compose.yaml
├── Dockerfile.api
├── Dockerfile.airflow
├── requirements.txt
└── .env                             # Secrets (never committed)
```

---

## Prerequisites

| Tool | Link |
|------|------|
| Docker Desktop | https://www.docker.com/products/docker-desktop |
| Node.js 18+ (for the frontend) | https://nodejs.org |
| Python 3.11+ (optional, for local API/tests) | https://www.python.org |

---

## Setup

### 1. Clone

```bash
git clone https://github.com/kaoutharaa/job-intelligent.git
cd job-intelligent
```

### 2. Create your `.env`

```env
# Airflow
FERNET_KEY=your_generated_fernet_key
SECRET_KEY=any_random_string

# France-Travail API credentials
FT_CLIENT_ID_api=your_client_id
FT_CLIENT_SECRET_api=your_client_secret

# API auth
JWT_SECRET=your_stable_random_secret     # keep constant so sessions survive restarts
# CORS_ORIGINS=http://localhost:5173      # optional; defaults to local Vite/CRA ports
```

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate a JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> `.env` is git-ignored — never commit it.

### 3. Initialize Airflow (first run only)

```bash
docker compose up airflow-init
```

If it exits with code 1, run `docker compose down -v` and retry.

### 4. Start the stack

```bash
docker compose up -d
```

This starts PostgreSQL, Selenium Chrome, the FastAPI service, and the Airflow webserver + scheduler.

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Service endpoints

| Service | URL | Notes |
|---------|-----|-------|
| API | http://localhost:8000 | `GET /health`, docs at `/docs` |
| API docs (Swagger) | http://localhost:8000/docs | |
| Frontend (Vite dev) | http://localhost:5173 | |
| Airflow UI | http://localhost:8080 | login `admin` / `admin`, DAG `daily_job_scraping` |
| Selenium noVNC | http://localhost:7900 | watch the browser scrape live |

> **Compose service names** (`api`, `postgres`, `airflow-scheduler`) are used for `docker compose logs`; **container names** (`job_api`, `job_postgres`, `job_airflow_scheduler`) are used for `docker exec`.

---

## API overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | DB connectivity check |
| `GET` | `/jobs` | List/filter gold jobs (source, category, location, title, pagination) |
| `GET` | `/jobs/search/{keyword}` | Full-text search (Postgres `tsvector`) |
| `GET` | `/stats`, `/stats/skills`, `/stats/timeline` | Aggregates for dashboards |
| `GET` | `/layers` | Row counts per Medallion layer |
| `POST` | `/recommend` | TF-IDF job matching from a title and/or uploaded CV (PDF) |
| `POST` | `/register`, `/login` | Return a JWT `access_token` + public user fields |
| `GET` | `/analysis/me` | Caller's most recent saved analysis (auth required) |

**Auth model:** `/register` and `/login` issue a JWT. Protected routes derive the user id from the bearer token — never from client input. `/recommend` accepts an optional token and only saves history when authenticated.

---

## ETL pipeline

Run the full Medallion ETL outside Airflow:

```bash
python scrapers/eda_pipeline.py
```

- **Bronze → Silver:** cleans text, standardizes titles, normalizes locations/dates, extracts skills, categorizes jobs (rebuilds each silver table per run).
- **Silver → Gold:** merges both sources, deduplicates globally by `job_url`, rebuilds `gold_jobs`, and exports `scrapers/data/gold_jobs.csv` and `.json`.

---

## Tests

```bash
python -m pytest tests/ -q
```

`tests/test_auth.py` covers password hashing and JWT helpers (no database required).

---

## Useful commands

```bash
docker compose up -d                       # start everything
docker compose down                        # stop (keeps data)
docker compose down -v                     # stop and wipe the DB volume
docker compose build api                   # rebuild the API image after code/dep changes
docker compose logs -f airflow-scheduler   # follow scheduler logs
docker exec -it job_postgres psql -U admin -d job_intelligent   # DB shell
```

> The API image bakes in `api/api.py`, so after backend changes run `docker compose build api && docker compose up -d api`. DAG and scraper files are bind-mounted and update live.

---

## Troubleshooting

**`airflow-init` exits with code 1** → `docker compose down -v`, then `docker compose up airflow-init` again.

**Sessions reset on every API restart** → set a stable `JWT_SECRET` in `.env`; without it the API uses a random per-restart secret.

**`/recommend` returns no matches** → confirm `gold_jobs` has data via `GET /layers`; run the ETL if the gold layer is empty.

**Scrapers return 0 jobs** → LinkedIn may have changed its HTML; check `docker compose logs -f airflow-scheduler`.

---

## Domain

The active target domain is **data / AI and adjacent tech roles, primarily in Morocco** (Data Scientist, Data Engineer, ML/MLOps Engineer, BI, NLP, AI Engineer, Data Architect, Big Data). Adjust the keyword lists in the scrapers to change coverage.
