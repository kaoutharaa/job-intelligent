-- Unified jobs table — Projet Job Intelligent
-- Runs automatically when PostgreSQL container starts for the first time.

CREATE TABLE IF NOT EXISTS jobs (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(255),
    company        VARCHAR(255),
    location       VARCHAR(255),
    date_posted    VARCHAR(100),
    job_url        TEXT UNIQUE,        -- deduplication key across all sources
    search_keyword VARCHAR(100),
    scraped_at     TIMESTAMP,
    salary         VARCHAR(255),       -- Indeed only, empty string for LinkedIn
    contract_type  VARCHAR(100),       -- Indeed only, empty string for LinkedIn
    source         VARCHAR(50)         -- 'linkedin' or 'indeed'
);

-- Index for fast filtering by source and keyword in Power BI
CREATE INDEX IF NOT EXISTS idx_jobs_source  ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_keyword ON jobs(search_keyword);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at);