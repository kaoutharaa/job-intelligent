# Job Intelligent — Daily Job Scraping Pipeline

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

Open `.env` and replace the placeholder values:

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
| Language | Python 3.11 |