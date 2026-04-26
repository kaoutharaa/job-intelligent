-- ============================================================================
-- RECOMMENDER SYSTEM SCHEMA
-- Tables pour le système de recommandation basé sur CV
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- CANDIDATE PROFILES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS candidate_profiles (
    id                BIGSERIAL PRIMARY KEY,
    full_name         TEXT,
    email             TEXT,
    current_title     TEXT,
    years_experience  INTEGER DEFAULT 0,
    skills            TEXT[],
    languages         TEXT[],
    desired_titles    TEXT[],
    desired_locations TEXT[],
    desired_contract  TEXT[],
    min_salary        INTEGER,
    remote_ok         BOOLEAN DEFAULT TRUE,
    profile_summary   TEXT,
    embedding         VECTOR(768),  -- pgvector embedding
    embedded_at       TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- RECOMMENDATION LOGS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS recommendation_logs (
    id                BIGSERIAL PRIMARY KEY,
    candidate_id      BIGINT REFERENCES candidate_profiles(id),
    job_id            TEXT NOT NULL,
    semantic_score    FLOAT,
    keyword_score     FLOAT,
    final_score       FLOAT,
    recommended_at    TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_candidate_created ON candidate_profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendation_candidate ON recommendation_logs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_date ON recommendation_logs(recommended_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- FUNCTIONS FOR VECTOR SEARCH
-- ─────────────────────────────────────────────────────────────────────────────

-- Function to match jobs using pgvector
CREATE OR REPLACE FUNCTION match_jobs(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.2,
    match_count INT DEFAULT 50
)
RETURNS TABLE(
    job_id TEXT,
    title TEXT,
    company TEXT,
    location_normalized TEXT,
    contract_type TEXT,
    keywords TEXT[],
    source TEXT,
    job_url TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sj.job_id,
        sj.title,
        sj.company,
        sj.location_normalized,
        sj.contract_type,
        sj.keywords,
        sj.source,
        sj.job_url,
        1 - (sj.embedding <=> query_embedding) AS similarity
    FROM silver_jobs sj
    WHERE sj.embedding IS NOT NULL
      AND 1 - (sj.embedding <=> query_embedding) > match_threshold
    ORDER BY sj.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- PERMISSIONS
-- ─────────────────────────────────────────────────────────────────────────────

GRANT ALL ON TABLE candidate_profiles TO anon;
GRANT ALL ON TABLE candidate_profiles TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE candidate_profiles_id_seq TO anon;
GRANT USAGE, SELECT ON SEQUENCE candidate_profiles_id_seq TO authenticated;

GRANT ALL ON TABLE recommendation_logs TO anon;
GRANT ALL ON TABLE recommendation_logs TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE recommendation_logs_id_seq TO anon;
GRANT USAGE, SELECT ON SEQUENCE recommendation_logs_id_seq TO authenticated;

GRANT EXECUTE ON FUNCTION match_jobs(VECTOR, FLOAT, INT) TO anon;
GRANT EXECUTE ON FUNCTION match_jobs(VECTOR, FLOAT, INT) TO authenticated;
-- ============================================================================
-- RECOMMENDER SYSTEM SCHEMA
-- Tables pour le système de recommandation basé sur CV
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- CANDIDATE PROFILES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS candidate_profiles (
    id                BIGSERIAL PRIMARY KEY,
    full_name         TEXT,
    email             TEXT,
    current_title     TEXT,
    years_experience  INTEGER DEFAULT 0,
    skills            TEXT[],
    languages         TEXT[],
    desired_titles    TEXT[],
    desired_locations TEXT[],
    desired_contract  TEXT[],
    min_salary        INTEGER,
    remote_ok         BOOLEAN DEFAULT TRUE,
    profile_summary   TEXT,
    embedding         VECTOR(768),  -- pgvector embedding
    embedded_at       TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- RECOMMENDATION LOGS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS recommendation_logs (
    id                BIGSERIAL PRIMARY KEY,
    candidate_id      BIGINT REFERENCES candidate_profiles(id),
    job_id            TEXT NOT NULL,  -- référence vers silver_jobs.job_id
    semantic_score    FLOAT,
    keyword_score     FLOAT,
    final_score       FLOAT,
    alpha             FLOAT,
    recommended_at    TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────

-- Vector similarity search
CREATE INDEX IF NOT EXISTS idx_candidate_embedding ON candidate_profiles USING ivfflat (embedding vector_cosine_ops);

-- Recommendation logs
CREATE INDEX IF NOT EXISTS idx_recommendation_candidate ON recommendation_logs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_job ON recommendation_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_date ON recommendation_logs(recommended_at DESC);

-- Candidate profiles
CREATE INDEX IF NOT EXISTS idx_candidate_created ON candidate_profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_title ON candidate_profiles(current_title);

-- ─────────────────────────────────────────────────────────────────────────────
-- FUNCTIONS FOR VECTOR SEARCH
-- ─────────────────────────────────────────────────────────────────────────────

-- Function to match jobs using pgvector
CREATE OR REPLACE FUNCTION match_jobs(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.2,
    match_count INT DEFAULT 50
)
RETURNS TABLE(
    job_id TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    contract_type TEXT,
    skills TEXT[],
    source TEXT,
    url TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sj.job_id,
        sj.title,
        sj.company,
        sj.location_normalized,
        sj.contract_type,
        sj.keywords,
        sj.source,
        sj.job_url,
        1 - (sj.embedding <=> query_embedding) AS similarity
    FROM silver_jobs sj
    WHERE sj.embedding IS NOT NULL
      AND 1 - (sj.embedding <=> query_embedding) > match_threshold
    ORDER BY sj.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- PERMISSIONS
-- ─────────────────────────────────────────────────────────────────────────────

GRANT ALL ON TABLE candidate_profiles TO anon;
GRANT ALL ON TABLE candidate_profiles TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE candidate_profiles_id_seq TO anon;
GRANT USAGE, SELECT ON SEQUENCE candidate_profiles_id_seq TO authenticated;

GRANT ALL ON TABLE recommendation_logs TO anon;
GRANT ALL ON TABLE recommendation_logs TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE recommendation_logs_id_seq TO anon;
GRANT USAGE, SELECT ON SEQUENCE recommendation_logs_id_seq TO authenticated;

-- Grant execute on the function
GRANT EXECUTE ON FUNCTION match_jobs(VECTOR, FLOAT, INT) TO anon;
GRANT EXECUTE ON FUNCTION match_jobs(VECTOR, FLOAT, INT) TO authenticated;