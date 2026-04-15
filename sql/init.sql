-- =============================================================================
-- MEDALLION ARCHITECTURE — Projet Job Intelligent
-- =============================================================================
-- BRONZE : raw data, one table per source, no indexes, no transformation
-- SILVER : cleaned data, one table per source, light indexes
-- GOLD   : unified, enriched, fully indexed for Power BI and NLP
-- =============================================================================

-- ─── BRONZE LAYER ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS bronze_linkedin (
    id             SERIAL PRIMARY KEY,
    title          TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    TEXT,
    job_url        TEXT UNIQUE,
    search_keyword TEXT,
    scraped_at     TEXT,
    salary         TEXT,
    contract_type  TEXT,
    source         TEXT DEFAULT 'linkedin',
    ingested_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze_france_travail (
    id             SERIAL PRIMARY KEY,
    title          TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    TEXT,
    job_url        TEXT UNIQUE,
    search_keyword TEXT,
    scraped_at     TEXT,
    salary         TEXT,
    contract_type  TEXT,
    source         TEXT DEFAULT 'france_travail',
    ingested_at    TIMESTAMP DEFAULT NOW()
);

-- ─── SILVER LAYER ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS silver_linkedin (
    id             SERIAL PRIMARY KEY,
    title          TEXT,
    title_raw      TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    DATE,
    job_url        TEXT UNIQUE,
    search_keyword TEXT,
    scraped_at     TIMESTAMP,
    salary         TEXT,
    contract_type  TEXT,
    skills         TEXT,
    category       TEXT,
    source         TEXT DEFAULT 'linkedin',
    processed_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_silver_linkedin_category ON silver_linkedin(category);
CREATE INDEX IF NOT EXISTS idx_silver_linkedin_date     ON silver_linkedin(date_posted);

CREATE TABLE IF NOT EXISTS silver_france_travail (
    id             SERIAL PRIMARY KEY,
    title          TEXT,
    title_raw      TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    DATE,
    job_url        TEXT UNIQUE,
    search_keyword TEXT,
    scraped_at     TIMESTAMP,
    salary         TEXT,
    contract_type  TEXT,
    skills         TEXT,
    category       TEXT,
    source         TEXT DEFAULT 'france_travail',
    processed_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_silver_ft_category ON silver_france_travail(category);
CREATE INDEX IF NOT EXISTS idx_silver_ft_date     ON silver_france_travail(date_posted);

-- ─── GOLD LAYER ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS gold_jobs (
    id             SERIAL PRIMARY KEY,
    title          TEXT,
    title_raw      TEXT,
    company        TEXT,
    location       TEXT,
    date_posted    DATE,
    job_url        TEXT UNIQUE,
    search_keyword TEXT,
    scraped_at     TIMESTAMP,
    salary         TEXT,
    contract_type  TEXT,
    skills         TEXT,
    category       TEXT,
    source         TEXT,
    processed_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gold_category  ON gold_jobs(category);
CREATE INDEX IF NOT EXISTS idx_gold_source    ON gold_jobs(source);
CREATE INDEX IF NOT EXISTS idx_gold_date      ON gold_jobs(date_posted);
CREATE INDEX IF NOT EXISTS idx_gold_location  ON gold_jobs(location);
CREATE INDEX IF NOT EXISTS idx_gold_title     ON gold_jobs(title);
CREATE INDEX IF NOT EXISTS idx_gold_keyword   ON gold_jobs(search_keyword);
CREATE INDEX IF NOT EXISTS idx_gold_scraped   ON gold_jobs(scraped_at);