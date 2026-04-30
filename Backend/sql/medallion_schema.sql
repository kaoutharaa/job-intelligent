-- ─────────────────────────────────────────────────────────────────────────────
-- SILVER LAYER
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS silver_jobs (
    id                  BIGSERIAL PRIMARY KEY,
    job_id              TEXT UNIQUE NOT NULL,
    title               TEXT NOT NULL,
    title_standardized  TEXT NOT NULL,
    company             TEXT NOT NULL,
    location            TEXT,
    location_normalized TEXT,
    date_posted         DATE,
    scraped_at          TIMESTAMP DEFAULT NOW(),
    job_url             TEXT,
    salary_min          NUMERIC(10,2),
    salary_max          NUMERIC(10,2),
    salary_currency     TEXT,
    contract_type       TEXT,
    source              TEXT NOT NULL,
    keywords            TEXT[],
    job_category        TEXT,
    seniority_level     TEXT,
    is_valid            BOOLEAN DEFAULT TRUE,
    validation_errors   TEXT[],
    last_updated        TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- GOLD LAYER
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS gold_daily_jobs_snapshot (
    id                      BIGSERIAL PRIMARY KEY,
    snapshot_date           DATE NOT NULL,
    source                  TEXT NOT NULL,
    title_standardized      TEXT NOT NULL,
    total_jobs              INT DEFAULT 0,
    avg_salary_min          NUMERIC(10,2),
    avg_salary_max          NUMERIC(10,2),
    locations               TEXT[],
    top_companies           TEXT[],
    dominant_contract_types TEXT[],
    created_at              TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (snapshot_date, source, title_standardized)
);

CREATE TABLE IF NOT EXISTS gold_company_stats (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL UNIQUE,
    total_jobs      INT DEFAULT 0,
    avg_salary_min  NUMERIC(10,2),
    avg_salary_max  NUMERIC(10,2),
    top_titles      TEXT[],
    last_updated    TIMESTAMP DEFAULT NOW(),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold_location_stats (
    id              BIGSERIAL PRIMARY KEY,
    location        TEXT NOT NULL UNIQUE,
    total_jobs      INT DEFAULT 0,
    avg_salary_min  NUMERIC(10,2),
    avg_salary_max  NUMERIC(10,2),
    top_titles      TEXT[],
    top_companies   TEXT[],
    last_updated    TIMESTAMP DEFAULT NOW(),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold_job_title_insights (
    id                      BIGSERIAL PRIMARY KEY,
    title_standardized      TEXT NOT NULL UNIQUE,
    total_jobs              INT DEFAULT 0,
    avg_salary_min          NUMERIC(10,2),
    avg_salary_max          NUMERIC(10,2),
    salary_median           NUMERIC(10,2),
    top_companies           TEXT[],
    top_locations           TEXT[],
    common_contract_types   TEXT[],
    common_keywords         TEXT[],
    seniority_distribution  JSONB,
    market_demand_trend     TEXT,
    last_updated            TIMESTAMP DEFAULT NOW(),
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold_monthly_trends (
    id                      BIGSERIAL PRIMARY KEY,
    year_month              DATE NOT NULL,
    source                  TEXT NOT NULL,
    new_jobs_count          INT DEFAULT 0,
    unique_companies        INT DEFAULT 0,
    avg_salary_min          NUMERIC(10,2),
    avg_salary_max          NUMERIC(10,2),
    top_job_titles          TEXT[],
    top_locations           TEXT[],
    created_at              TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (year_month, source)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- METADATA TABLE
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS medallion_metadata (
    id              BIGSERIAL PRIMARY KEY,
    layer           TEXT NOT NULL,
    table_name      TEXT NOT NULL,
    operation       TEXT NOT NULL,
    rows_processed  INT,
    rows_inserted   INT,
    rows_updated    INT,
    execution_start TIMESTAMP,
    execution_end   TIMESTAMP,
    status          TEXT,
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES (POSTGRESQL CORRECT WAY)
-- ─────────────────────────────────────────────────────────────────────────────

-- SILVER
CREATE INDEX IF NOT EXISTS idx_silver_title 
ON silver_jobs(title_standardized);

CREATE INDEX IF NOT EXISTS idx_silver_company 
ON silver_jobs(company);

CREATE INDEX IF NOT EXISTS idx_silver_location 
ON silver_jobs(location_normalized);

CREATE INDEX IF NOT EXISTS idx_silver_source 
ON silver_jobs(source);

CREATE INDEX IF NOT EXISTS idx_silver_date_posted 
ON silver_jobs(date_posted);

CREATE INDEX IF NOT EXISTS idx_silver_scraped_at 
ON silver_jobs(scraped_at);

-- GOLD COMPANY
CREATE INDEX IF NOT EXISTS idx_gold_company_total_jobs 
ON gold_company_stats(total_jobs DESC);

-- GOLD LOCATION
CREATE INDEX IF NOT EXISTS idx_gold_location_total_jobs 
ON gold_location_stats(total_jobs DESC);

-- GOLD JOB TITLE
CREATE INDEX IF NOT EXISTS idx_gold_title_total_jobs 
ON gold_job_title_insights(total_jobs DESC);

CREATE INDEX IF NOT EXISTS idx_gold_title_salary 
ON gold_job_title_insights(salary_median DESC);

-- SNAPSHOT
CREATE INDEX IF NOT EXISTS idx_gold_snapshot_date 
ON gold_daily_jobs_snapshot(snapshot_date);

CREATE INDEX IF NOT EXISTS idx_gold_snapshot_source 
ON gold_daily_jobs_snapshot(source);

CREATE INDEX IF NOT EXISTS idx_gold_snapshot_title 
ON gold_daily_jobs_snapshot(title_standardized);

-- MONTHLY
CREATE INDEX IF NOT EXISTS idx_gold_monthly_year 
ON gold_monthly_trends(year_month DESC);

-- METADATA
CREATE INDEX IF NOT EXISTS idx_metadata_layer 
ON medallion_metadata(layer);

CREATE INDEX IF NOT EXISTS idx_metadata_table 
ON medallion_metadata(table_name);

CREATE INDEX IF NOT EXISTS idx_metadata_created 
ON medallion_metadata(created_at DESC);