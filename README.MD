# Job Intelligent — Daily Job Scraping Pipeline

Automated data pipeline that scrapes tech job listings from **LinkedIn** and **France-Travail** daily, cleans and standardizes them via an ETL pipeline, stores them in **Supabase** (cloud PostgreSQL), and orchestrates everything with **Apache Airflow** running inside **Docker**.

---

## Project Structure

```
job_intelligent/
├── dags/
│   └── medallion_pipeline_dag.py   # Airflow DAG — Bronze/Silver/Gold pipeline
├── scrapers/
│   ├── scrapping_linkedin.py       # LinkedIn scraper
│   ├── scrapping_france_travail.py # France-Travail scraper
│   ├── silver_transformation.py    # Bronze → Silver ETL
│   ├── gold_transformation.py      # Silver → Gold aggregations
│   ├── db.py                       # Supabase REST push helper
│   ├── config.py                   # Shared pipeline configuration
│   ├── utils.py                    # Shared helper functions
│   └── data/                       # Local exports
│       ├── jobradar_clean.csv      # Power BI ready
│       ├── jobradar_clean.json     # NLP ready
│       └── jobradar.db             # SQLite backup
├── sql/
│   ├── init.sql                    # Airflow PostgreSQL init
│   └── medallion_schema.sql        # Supabase medallion table schema
├── docker-compose.yml              # All services
├── Dockerfile.airflow              # Custom Airflow image
├── requirements.txt                # Python dependencies
└── .env                            # Secret keys (never commit)
```

---

## Architecture

```
LinkedIn scraper ──┐
                   ├──► push_to_db (Supabase: jobs) ──► ETL pipeline ──► Supabase: jobs_clean
France-Travail  ──┘                                                   ──► CSV / JSON / SQLite
```

- `jobs` table — raw scraped data, append-only, managed by Airflow
- `silver_jobs` table — cleaned, validated and enriched Silver data
- `gold_*` tables — aggregated analytics results for BI and reporting

---

## Prerequisites

| Tool | Download |
|------|----------|
| Docker Desktop | https://www.docker.com/products/docker-desktop |
| Git | https://git-scm.com |
| Python 3.11+ | https://www.python.org |

Verify Docker is running:
```bash
docker --version
docker compose version
```

---

## Setup — Step by Step

### 1. Clone the repository

```bash
git clone https://github.com/kaoutharaa/job-intelligent.git
cd job-intelligent
```

### 2. Configure environment variables

Create a `.env` file at the project root:

```env
# Airflow
FERNET_KEY=paste_your_generated_fernet_key_here
SECRET_KEY=any_random_string_you_choose

# France-Travail API
FT_CLIENT_ID_api=your_france_travail_client_id
FT_CLIENT_SECRET_api=your_france_travail_client_secret

# Supabase
SUPABASE_API_URL=https://your-project.supabase.co
SUPABASE_API_KEY=your_supabase_anon_key
```

Generate your Fernet key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

> ⚠️ Never commit `.env` to Git. It is already in `.gitignore`.

### 3. Create Supabase tables

Run the current medallion schema in your **Supabase SQL Editor** by copying the contents of `sql/medallion_schema.sql` or uploading it.

This will create the Bronze/Silver/Gold pipeline tables:

- `jobs` (Bronze raw data)
- `silver_jobs` (Silver cleaned and validated data)
- `gold_daily_jobs_snapshot`
- `gold_company_stats`
- `gold_location_stats`
- `gold_job_title_insights`
- `gold_monthly_trends`
- `medallion_metadata`

If the `jobs` table already exists, do not recreate it. Only run the schema for the new `silver_jobs` and `gold_*` tables.

### 4. Build and initialize Airflow

```bash
# First time only
docker compose up airflow-init
```

Wait until you see:
```
User "admin" created with role "Admin"
job_airflow_init exited with code 0
```

### 5. Start all services

```bash

docker compose up -d
```

### 6. Verify everything is running

```bash
docker compose ps
```

Expected output:
```
job_postgres            running   → port 5432
job_selenium            running   → port 4444
job_airflow_webserver   running   → port 8080
job_airflow_scheduler   running
```

---

## Using the Pipeline

### Airflow UI
Open **http://localhost:8080** — login: `admin` / `admin`

- Find the DAG `medallion_daily_pipeline`
- Toggle it **ON**
- Click **▶ Trigger DAG** to run manually

The pipeline runs automatically every day at **12:00 UTC**.

### Pipeline Flow

```
extract_linkedin       ─┐
                        ├─► push_to_bronze
extract_france_travail ─┘
                        └─► silver_transform ─► gold_transform ─► monitor_medallion
```

| Task | Description |
|------|-------------|
| `extract_linkedin` | Scrapes LinkedIn via Selenium (timeout: 60 min) |
| `extract_france_travail` | Calls France-Travail API (timeout: 10 min) |
| `push_to_bronze` | Pushes raw jobs to Supabase `jobs` table |
| `silver_transform` | Cleans, enriches, validates → `silver_jobs` |
| `gold_transform` | Aggregates Silver data into `gold_*` tables |
| `monitor_medallion` | Logs pipeline completion status |

### Watch Chrome scraping live
Open **http://localhost:7900** to see the Selenium browser in action.

---

## ETL Pipeline

The ETL can also be run independently outside Airflow:

```bash
cd scrapers
python etl_pipeline.py            # one-time run
python etl_pipeline.py --schedule # runs daily at 12:30 UTC
```

### What the ETL does

- Reads all jobs from Supabase `jobs` table
- Standardizes job titles (e.g. "data eng." → "Data Engineer")
- Extracts skills from title/company (Python, SQL, Spark, etc.)
- Categorizes jobs (Data & AI, DevOps & Cloud, Software Dev, etc.)
- Deduplicates by title + company + location
- Pushes clean data to Supabase `jobs_clean`
- Exports CSV, JSON, and SQLite to `scrapers/data/`

---

## Checking the Data

### Supabase dashboard
Go to **https://supabase.com/dashboard/project/your-project-id** → Table Editor

### Local files (after ETL runs)
```
scrapers/data/jobradar_clean.csv   → import into Power BI
scrapers/data/jobradar_clean.json  → use for NLP / recommendation engine
scrapers/data/jobradar.db          → SQLite backup
```

### Terminal (quick stats)
```bash
docker exec -it job_postgres psql -U admin -d job_intelligent
```

---

## Useful Commands

```bash
# Start everything
docker compose up -d

# Stop everything (keeps data)
docker compose down

# Stop and DELETE all data (full reset)
docker compose down -v

# Rebuild the Airflow image
docker compose build --no-cache

# View live logs
docker compose logs -f airflow-scheduler

# View ETL logs
docker compose logs -f job_airflow_scheduler | grep ETL
```

---

## Keywords Scraped

Currently targeting **data roles in Morocco**:

- Data Scientist, Data Engineer, Data Analyst
- Machine Learning Engineer, MLOps Engineer
- Business Intelligence, NLP Engineer, AI Engineer
- Data Architect, Big Data Engineer

> To add keywords, edit the `KEYWORDS` list in `scrapping_linkedin.py` and `scrapping_france_travail.py`, then restart the containers.

---

## Troubleshooting

**`airflow-init` exits with code 1**
→ Run `docker compose down -v` then `docker compose up airflow-init` again.

**`push_to_db` fails with SUPABASE_API_KEY missing**
→ Make sure `SUPABASE_API_KEY` is set in `.env` and containers were restarted after adding it.

**ETL returns 0 jobs**
→ Check that `jobs` table has data in Supabase dashboard first.

**Scrapers return 0 jobs**
→ LinkedIn may have changed their HTML. Check the scheduler logs for details.

**Docker can't connect to the internet during build**
→ Docker Desktop → Settings → Docker Engine → add `"dns": ["8.8.8.8", "8.8.4.4"]` → Apply & Restart.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Orchestration | Apache Airflow 2.10.4 |
| Scraping | Selenium + BeautifulSoup4 |
| Browser automation | Selenium Grid (Chrome) |
| Database (cloud) | Supabase (PostgreSQL) |
| Database (local) | PostgreSQL 15 + SQLite |
| ETL | Python (pandas, requests) |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 |

---

## Team

Shared Supabase project — both team members read/write the same `jobs` and `jobs_clean` tables.
To add a new team member: **Supabase dashboard → Organization → Members → Invite**.