-- ============================================================================
-- Add Embedding Support to Silver Layer
-- ============================================================================
-- This migration adds vector embedding columns to silver_jobs table
-- SAFE: Only adds new columns, doesn't modify existing structure
-- IMPACT: None on existing Power BI dashboards

-- ─────────────────────────────────────────────────────────────────────────
-- 1. Enable pgvector extension (if not already enabled)
-- ─────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────────────────
-- 2. Add embedding columns to silver_jobs
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE IF EXISTS silver_jobs
ADD COLUMN IF NOT EXISTS embedding VECTOR(768);

ALTER TABLE IF EXISTS silver_jobs
ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMP;

-- ─────────────────────────────────────────────────────────────────────────
-- 3. Create IVFFlat index for vector similarity search
-- ─────────────────────────────────────────────────────────────────────────
-- IVFFlat is fast for high-dimensional vectors (768-dim embeddings)
-- Uses cosine distance for similarity: SELECT ... ORDER BY embedding <=> query_embedding
CREATE INDEX IF NOT EXISTS idx_silver_embedding 
ON silver_jobs USING ivfflat (embedding vector_cosine_ops);

-- ─────────────────────────────────────────────────────────────────────────
-- 4. Verify the changes
-- ─────────────────────────────────────────────────────────────────────────
-- Run this query to confirm:
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'silver_jobs' AND column_name LIKE '%embedding%';
