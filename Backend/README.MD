# Job Intelligent — Medallion ETL Pipeline

Automated data warehouse pipeline that scrapes tech job listings from **LinkedIn** and **France-Travail** daily, transforms them through a **Medallion Architecture** (Bronze → Silver → Gold), stores analytics-ready data in **Supabase** (cloud PostgreSQL), and orchestrates everything with **Apache Airflow** running inside **Docker**.

---

## 🏗️ Medallion Architecture Overview

```
Raw Scraping ──► BRONZE Layer ──► SILVER Layer ──► GOLD Layer ──► BI Dashboard
(LinkedIn/FT)     (Raw Jobs)       (Clean Data)     (Analytics)     (Power BI/Tableau)
```

### Bronze Layer
- **Table**: `jobs`
- **Purpose**: Raw scraped data, append-only
- **Data**: Unstructured job postings as scraped

### Silver Layer
- **Table**: `silver_jobs`
- **Purpose**: Cleaned, validated, enriched data
- **Transformations**: Standardization, deduplication, skill extraction, validation

### Gold Layer (Analytics-Ready)
- **Tables**:
  - `gold_daily_jobs_snapshot` — Daily job market trends by source & title
  - `gold_company_stats` — Company hiring analytics
  - `gold_location_stats` — Location-based job insights
  - `gold_job_title_insights` — Job title demand & salary analysis
  - `gold_monthly_trends` — Time-series hiring patterns
- **Purpose**: Aggregated data for BI dashboards and reporting

### Metadata Layer
- **Table**: `medallion_metadata`
- **Purpose**: Pipeline execution tracking (currently empty, can be implemented)

---

## 📁 Project Structure

```
job_intelligent/
├── dags/
│   └── medallion_pipeline_dag.py   # Airflow DAG — Complete medallion pipeline
├── scrapers/
│   ├── scrapping_linkedin.py       # LinkedIn scraper (Selenium)
│   ├── scrapping_france_travail.py # France-Travail API scraper
│   ├── silver_transformation.py    # Bronze → Silver ETL
│   ├── gold_transformation.py      # Silver → Gold aggregations
│   ├── db.py                       # Supabase REST API helpers
│   ├── config.py                   # Pipeline configuration
│   ├── utils.py                    # Shared utilities
│   └── validate_medallion.py       # Pipeline validation script
├── sql/
│   ├── init.sql                    # Airflow PostgreSQL init
│   ├── medallion_schema.sql        # Supabase medallion tables
│   └── gold_analytics_queries.sql  # 50+ BI-ready queries
├── Medallion_ETL_Pipeline.ipynb    # Interactive demo notebook
├── docker-compose.yaml             # All services orchestration
├── Dockerfile.airflow              # Custom Airflow image
├── requirements.txt                # Python dependencies
├── test.py                         # Unit tests
├── validate_medallion.py           # Pipeline health checks
├── chromedriver-win64/             # Selenium Chrome driver
└── logs/                           # Airflow execution logs
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Git
- Python 3.11+

### 1. Setup Environment
```bash
git clone <your-repo>
cd job_intelligent
```

Create `.env`:
```env
SUPABASE_API_URL=https://your-project.supabase.co
SUPABASE_API_KEY=your-anon-key
FT_CLIENT_ID_api=your-france-travail-client-id
FT_CLIENT_SECRET_api=your-france-travail-secret
FERNET_KEY=generate-with-python-cryptography
SECRET_KEY=any-random-string
```

### 2. Initialize Database
Execute `sql/medallion_schema.sql` in Supabase SQL Editor to create all tables.

### 3. Launch Pipeline
```bash
docker compose up airflow-init
docker compose up -d
```

### 4. Access Airflow UI
- URL: http://localhost:8080
- Login: admin/admin
- Enable and trigger `medallion_daily_pipeline`

---

## 📊 BI Dashboard Setup

Connect your BI tool to Supabase and use **only the GOLD tables**:

### Recommended Dashboard Structure
```
📊 Job Market Dashboard
├── 📈 Overview
│   ├── Total active jobs (gold_daily_jobs_snapshot)
│   ├── Jobs by source (LinkedIn vs France-Travail)
│   └── Daily hiring trends (gold_monthly_trends)
│
├── 🏢 Company Insights
│   ├── Top hiring companies (gold_company_stats)
│   ├── Salary ranges by company
│   └── Company growth trends
│
├── 📍 Location Analytics
│   ├── Jobs by region (gold_location_stats)
│   ├── Salary by location
│   └── Remote vs office distribution
│
├── 💼 Job Title Trends
│   ├── Most demanded titles (gold_job_title_insights)
│   ├── Salary expectations
│   ├── Market demand (HIGH/MEDIUM/LOW)
│   └── Top skills per title
│
└── 📅 Time Series
    ├── Monthly hiring volume (gold_monthly_trends)
    ├── Seasonal patterns
    └── YoY growth
```

### Connection Details
- **Host**: your-project.supabase.co
- **Port**: 5432
- **Database**: postgres
- **Tables**: gold_* (skip bronze/silver for dashboards)

### Sample Queries
See `sql/gold_analytics_queries.sql` for 50+ ready-to-use BI queries.

---

## 🛠️ ETL Pipeline Details

### Pipeline Tasks
1. **extract_linkedin** — Scrape LinkedIn jobs
2. **extract_france_travail** — Scrape France-Travail jobs  
3. **push_to_bronze** — Store raw data in `jobs`
4. **silver_transform** — Clean → `silver_jobs`
5. **gold_transform** — Aggregate → `gold_*` tables
6. **monitor_medallion** — Log completion

### Key Transformations
- **Title Standardization**: "data eng." → "Data Engineer"
- **Skill Extraction**: Python, SQL, Spark, etc.
- **Salary Parsing**: €50k-70k ranges
- **Location Normalization**: "Paris, France" → "Paris"
- **Deduplication**: By job_id hash
- **Validation**: Required fields, length checks

---

## 🔧 File Deletion Impact

**Essential Files** (Do NOT delete):
- `docker-compose.yaml` — Service orchestration
- `dags/medallion_pipeline_dag.py` — Pipeline logic
- `scrapers/` — All ETL code
- `sql/medallion_schema.sql` — Database schema
- `.env` — Configuration (keep secure)

**Optional Files** (Safe to delete):
- `Medallion_ETL_Pipeline.ipynb` — Demo notebook only
- `logs/` — Regenerated on runs
- `test.py` — For development testing
- `validate_medallion.py` — Health checks
- `chromedriver-win64/` — Downloaded by Docker

**Consequences of Deleting Essential Files**:
- Pipeline breaks — no more automated runs
- Data processing stops
- BI dashboards lose data source
- Full rebuild required from backup

---

## 📋 Useful Commands

```bash
# Start pipeline
docker compose up -d

# View logs
docker compose logs -f airflow-scheduler

# Reset everything
docker compose down -v

# Run validation
python validate_medallion.py

# Manual ETL run
cd scrapers && python gold_transformation.py
```

---

## 🐛 Troubleshooting

- **Pipeline fails**: Check Airflow logs for error details
- **No data**: Verify Supabase connection and API keys
- **Scrapers timeout**: LinkedIn may have changed; update selectors
- **Gold tables empty**: Check Silver transformation succeeded first

---

## 🏷️ Tech Stack

- **Orchestration**: Apache Airflow 2.10.4
- **Scraping**: Selenium + BeautifulSoup4
- **Database**: Supabase (PostgreSQL)
- **ETL**: Python (pandas, requests)
- **Containerization**: Docker + Docker Compose
- **BI Ready**: Power BI, Tableau, Metabase compatible

---

## 📈 Current Status

✅ **Production Ready**
- Medallion architecture implemented
- Daily automated pipeline
- 8 tables created and populated
- BI dashboard ready
- Comprehensive validation suite

**Next Steps**:
1. Connect BI tool to gold_* tables
2. Create dashboards with provided queries
3. Monitor pipeline health
4. Add alerting for failures
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