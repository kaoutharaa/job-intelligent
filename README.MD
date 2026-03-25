<!-- # Job Intelligent — Daily Job Scraping Pipeline

Automated data pipeline that scrapes tech job listings from **LinkedIn** and **Indeed Morocco** daily, stores them in **PostgreSQL**, and orchestrates everything with **Apache Airflow** running inside **Docker**.

---

## Project Structure

```
job_intelligent/
├── dags/
│   └── job_scraping_dag.py       # Airflow DAG — daily pipeline
├── scrapers/
│   ├── scrapping_linkedin.py     # LinkedIn scraper
│   ├── scrapping_indeed.py       # Indeed scraper
│   └── db.py                     # PostgreSQL push helper
├── sql/
│   └── init.sql                  # Auto-creates the jobs table
├── docker-compose.yml            # All services
├── Dockerfile.airflow            # Custom Airflow image
├── requirements.txt              # Python dependencies
└── .env                          # Secret keys (generate before running)
```

---

## Prerequisites

Install these before anything else:

| Tool | Download |
|------|----------|
| Docker Desktop | https://www.docker.com/products/docker-desktop |
| Git | https://git-scm.com |
| DBeaver (optional, to browse DB) | https://dbeaver.io |

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

### 2. Generate your secret keys

Run this once in Python (any Python environment):

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Create `.env` file and replace the placeholder values:

```env
FERNET_KEY=paste_your_generated_key_here
SECRET_KEY=any_random_string_you_choose
```

> ⚠️ Never commit `.env` to Git. It is already in `.gitignore`.

### 3. Build and initialize

```bash
# First time only — builds the Docker image and initializes the Airflow database
docker compose up airflow-init
```

Wait until you see:
```
User "admin" created with role "Admin"
job_airflow_init exited with code 0
```

### 4. Start all services

```bash
docker compose up -d
```

### 5. Verify everything is running

```bash
docker compose ps
```

You should see 4 containers with status `running`:

```
job_postgres            running   → port 5432
job_selenium            running   → port 4444
job_airflow_webserver   running   → port 8080
job_airflow_scheduler   running
```

---

## Using the Pipeline

### Airflow UI
Open **http://localhost:8080** in your browser.

- Login: `admin` / `admin`
- Find the DAG `daily_job_scraping`
- Toggle it **ON**
- Click **▶ Trigger DAG** to run it manually

The pipeline runs automatically every day at **12:00 UTC**.

### Pipeline Flow

```
extract_linkedin ──┐
                   ├──► push_to_db ──► PostgreSQL
extract_indeed   ──┘
```

`extract_linkedin` and `extract_indeed` run **in parallel**, then `push_to_db` merges and inserts all results.

### Watch Chrome scraping live
Open **http://localhost:7900** to see the Selenium browser in action.

---

## Checking the Database

### Option A — Terminal (quick)

```bash
docker exec -it job_postgres psql -U admin -d job_intelligent
```

Then run SQL queries:

```sql
-- Total jobs
SELECT COUNT(*) FROM jobs;

-- By source
SELECT source, COUNT(*) FROM jobs GROUP BY source;

-- By keyword
SELECT search_keyword, COUNT(*) FROM jobs GROUP BY search_keyword ORDER BY COUNT(*) DESC;

-- Sample rows
SELECT title, company, location, source FROM jobs LIMIT 10;

-- Exit
\q
```

### Option B — DBeaver (visual)

Create a new PostgreSQL connection with:

```
Host     : localhost
Port     : 5432
Database : job_intelligent
Username : admin
Password : password
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

# Rebuild the Airflow image (after changing requirements.txt)
docker compose build --no-cache

# View live logs
docker compose logs -f airflow-scheduler

# View logs for a specific container
docker compose logs -f job_postgres
```

---

## Keywords Scraped

The scrapers currently target **data roles in Morocco**:

- Data Scientist, Data Engineer, Data Analyst
- Machine Learning Engineer, MLOps Engineer
- Business Intelligence, NLP Engineer, AI Engineer
- Data Architect, Big Data Engineer

> To add more keywords, edit the `KEYWORDS` list in `scrapers/scrapping_linkedin.py` and `scrapers/scrapping_indeed.py`, then restart the containers.

---

## Database Schema

```sql
CREATE TABLE jobs (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(255),
    company        VARCHAR(255),
    location       VARCHAR(255),
    date_posted    VARCHAR(100),
    job_url        TEXT UNIQUE,      -- deduplication key
    search_keyword VARCHAR(100),
    scraped_at     TIMESTAMP,
    salary         VARCHAR(255),     -- Indeed only
    contract_type  VARCHAR(100),     -- Indeed only
    source         VARCHAR(50)       -- 'linkedin' or 'indeed'
);
```

---

## Troubleshooting

**`airflow-init` exits with code 1**
→ Run `docker compose down -v` then `docker compose up airflow-init` again to reset.

**`push_to_db` fails**
→ Click the failed task in Airflow UI → Logs tab → check the error message.
→ Make sure `job_postgres` container is running: `docker compose ps`.

**Scrapers return 0 jobs**
→ LinkedIn and Indeed may have changed their HTML structure. Check the logs for the specific keyword that failed.

**Docker can't connect to the internet during build**
→ Open Docker Desktop → Settings → Docker Engine → add `"dns": ["8.8.8.8", "8.8.4.4"]` → Apply & Restart.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Orchestration | Apache Airflow 2.10.4 |
| Scraping | Selenium + BeautifulSoup4 |
| Browser | Selenium Grid (Chrome) |
| Database | PostgreSQL 15 |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 | -->






# Job Intelligent — Daily Job Scraping Pipeline

Automated data pipeline that scrapes tech job listings from **LinkedIn** and **France-Travail** daily, cleans and standardizes them via an ETL pipeline, stores them in **Supabase** (cloud PostgreSQL), and orchestrates everything with **Apache Airflow** running inside **Docker**.

---

## Project Structure

```
job_intelligent/
├── dags/
│   └── job_scraping_dag.py        # Airflow DAG — daily pipeline
├── scrapers/
│   ├── scrapping_linkedin.py      # LinkedIn scraper
│   ├── scrapping_france_travail.py # France-Travail scraper
│   ├── etl_pipeline.py            # ETL — clean + push to jobs_clean
│   ├── db.py                      # Supabase REST push helper
│   └── data/                      # Local outputs (CSV, JSON, SQLite)
│       ├── jobradar_clean.csv     # Power BI ready
│       ├── jobradar_clean.json    # NLP ready
│       └── jobradar.db            # SQLite backup
├── sql/
│   └── init.sql                   # Airflow PostgreSQL init
├── docker-compose.yml             # All services
├── Dockerfile.airflow             # Custom Airflow image
├── requirements.txt               # Python dependencies
└── .env                           # Secret keys (never commit)
```

---

## Architecture

```
LinkedIn scraper ──┐
                   ├──► push_to_db (Supabase: jobs) ──► ETL pipeline ──► Supabase: jobs_clean
France-Travail  ──┘                                                   ──► CSV / JSON / SQLite
```

- `jobs` table — raw scraped data, append-only, managed by Airflow
- `jobs_clean` table — deduplicated, standardized, enriched with skills & categories

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

Run these once in your **Supabase SQL Editor**:

```sql
-- Raw jobs table (managed by Airflow)
CREATE TABLE IF NOT EXISTS jobs (
    id             BIGSERIAL PRIMARY KEY,
    title          TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    TEXT,
    job_url        TEXT UNIQUE,
    search_keyword TEXT,
    scraped_at     TEXT,
    salary         TEXT,
    contract_type  TEXT,
    source         TEXT
);

-- Clean jobs table (managed by ETL pipeline)
CREATE TABLE IF NOT EXISTS jobs_clean (
    id             BIGSERIAL PRIMARY KEY,
    title          TEXT,
    title_raw      TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    TEXT,
    category       TEXT,
    skills         TEXT,
    job_url        TEXT,
    search_keyword TEXT,
    scraped_at     TEXT,
    source         TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Permissions
GRANT ALL ON TABLE jobs TO anon;
GRANT ALL ON TABLE jobs_clean TO anon;
GRANT USAGE, SELECT ON SEQUENCE jobs_clean_id_seq TO anon;

-- Indexes for Power BI and recommendation engine
CREATE INDEX IF NOT EXISTS idx_jobs_clean_category ON jobs_clean(category);
CREATE INDEX IF NOT EXISTS idx_jobs_clean_source   ON jobs_clean(source);
CREATE INDEX IF NOT EXISTS idx_jobs_clean_date     ON jobs_clean(date_posted);
```

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

- Find the DAG `daily_job_scraping`
- Toggle it **ON**
- Click **▶ Trigger DAG** to run manually

The pipeline runs automatically every day at **12:00 UTC**.

### Pipeline Flow

```
extract_linkedin       ─┐
                        ├─► push_to_db ─► run_etl
extract_france_travail ─┘
```

| Task | Description |
|------|-------------|
| `extract_linkedin` | Scrapes LinkedIn via Selenium (timeout: 60 min) |
| `extract_france_travail` | Calls France-Travail API (timeout: 10 min) |
| `push_to_db` | Pushes raw jobs to Supabase `jobs` table |
| `run_etl` | Cleans, deduplicates, enriches → `jobs_clean` |

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