-- ============================================================================
-- GOLD LAYER ANALYTICS QUERIES
-- Exemples de requêtes pour créer des dashboards et reports
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. MARCHÉ DE L'EMPLOI: Vue d'ensemble
-- ─────────────────────────────────────────────────────────────────────────────

-- Top 10 métiers par demande
SELECT 
    title_standardized,
    total_jobs,
    salary_median,
    market_demand_trend,
    common_keywords
FROM gold_job_title_insights
ORDER BY total_jobs DESC
LIMIT 10;

-- Top 10 entreprises recruteuses
SELECT 
    company,
    total_jobs,
    avg_salary_min,
    avg_salary_max,
    top_titles
FROM gold_company_stats
ORDER BY total_jobs DESC
LIMIT 10;

-- Localités avec plus d'offres
SELECT 
    location,
    total_jobs,
    avg_salary_min,
    avg_salary_max,
    top_companies
FROM gold_location_stats
WHERE total_jobs > 10
ORDER BY total_jobs DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. ANALYSE SALARIALE
-- ─────────────────────────────────────────────────────────────────────────────

-- Salaires médians par métier (top 15)
SELECT 
    title_standardized,
    salary_median,
    avg_salary_min,
    avg_salary_max,
    total_jobs
FROM gold_job_title_insights
WHERE salary_median IS NOT NULL
ORDER BY salary_median DESC
LIMIT 15;

-- Fourchette salariale par localité
SELECT 
    location,
    total_jobs,
    ROUND(avg_salary_min::numeric, 0) as min_salary,
    ROUND(avg_salary_max::numeric, 0) as max_salary,
    ROUND((avg_salary_max - avg_salary_min)::numeric, 0) as salary_range
FROM gold_location_stats
WHERE avg_salary_min IS NOT NULL AND total_jobs > 5
ORDER BY avg_salary_max DESC;

-- Comparaison salariale: Data Science vs Data Engineering vs Analytics
SELECT 
    title_standardized,
    total_jobs,
    ROUND(salary_median::numeric, 0) as median_salary,
    ROUND(avg_salary_min::numeric, 0) as avg_min,
    ROUND(avg_salary_max::numeric, 0) as avg_max
FROM gold_job_title_insights
WHERE title_standardized IN ('Data Scientist', 'Data Engineer', 'Data Analyst')
ORDER BY salary_median DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. ANALYSE PAR SENIORITY
-- ─────────────────────────────────────────────────────────────────────────────

-- Distribution seniority par métier (pour roles data)
SELECT 
    title_standardized,
    total_jobs,
    seniority_distribution,
    (seniority_distribution->>'Junior')::numeric as pct_junior,
    (seniority_distribution->>'Senior')::numeric as pct_senior,
    (seniority_distribution->>'Expert')::numeric as pct_expert
FROM gold_job_title_insights
WHERE title_standardized LIKE '%Data%' OR title_standardized LIKE '%Analyst%'
ORDER BY title_standardized;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. ANALYSE DES COMPÉTENCES REQUISES
-- ─────────────────────────────────────────────────────────────────────────────

-- Top 20 compétences pour Data Scientists
SELECT 
    title_standardized,
    common_keywords
FROM gold_job_title_insights
WHERE title_standardized = 'Data Scientist'
LIMIT 1;

-- Top 20 compétences pour Data Engineers
SELECT 
    title_standardized,
    common_keywords
FROM gold_job_title_insights
WHERE title_standardized = 'Data Engineer'
LIMIT 1;

-- Top 20 compétences pour DevOps
SELECT 
    title_standardized,
    common_keywords
FROM gold_job_title_insights
WHERE title_standardized LIKE '%DevOps%'
LIMIT 1;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. TENDANCES TEMPORELLES
-- ─────────────────────────────────────────────────────────────────────────────

-- Tendance mensuelle: nombre d'offres par source
SELECT 
    year_month,
    source,
    new_jobs_count,
    unique_companies
FROM gold_monthly_trends
ORDER BY year_month DESC, source;

-- Métiers en plus forte demande (dernière semaine)
SELECT 
    snapshot_date,
    title_standardized,
    total_jobs,
    source,
    avg_salary_min,
    avg_salary_max
FROM gold_daily_jobs_snapshot
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY snapshot_date DESC, total_jobs DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. ANALYSE COMPARÉE: LinkedIn vs France-Travail
-- ─────────────────────────────────────────────────────────────────────────────

-- Comparaison par source: nombre d'offres et salaires
SELECT 
    source,
    COUNT(DISTINCT title_standardized) as unique_jobs,
    SUM(CASE WHEN title_standardized = 'Data Scientist' THEN 1 ELSE 0 END) as data_scientist_count,
    SUM(CASE WHEN title_standardized = 'Data Engineer' THEN 1 ELSE 0 END) as data_engineer_count,
    ROUND(AVG(avg_salary_min)::numeric, 0) as avg_salary_across_source
FROM gold_daily_jobs_snapshot
GROUP BY source;

-- Métiers présents uniquement sur LinkedIn
WITH linkedin_jobs AS (
    SELECT DISTINCT title_standardized 
    FROM gold_daily_jobs_snapshot 
    WHERE source = 'linkedin'
),
france_travail_jobs AS (
    SELECT DISTINCT title_standardized 
    FROM gold_daily_jobs_snapshot 
    WHERE source = 'france_travail'
)
SELECT * FROM linkedin_jobs 
WHERE title_standardized NOT IN (SELECT * FROM france_travail_jobs);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. ANALYSE: TOP COMBINAISONS MÉTIER-LOCALITÉ
-- ─────────────────────────────────────────────────────────────────────────────

-- Meilleures opportunités: haute demande + bon salaire
SELECT 
    gs.location,
    gti.title_standardized,
    COALESCE(ds.total_jobs, 0) as jobs_in_location_for_title,
    gti.total_jobs as jobs_overall,
    ROUND(gti.salary_median::numeric, 0) as median_salary,
    gti.market_demand_trend
FROM gold_location_stats gs
CROSS JOIN gold_job_title_insights gti
LEFT JOIN gold_daily_jobs_snapshot ds 
    ON ds.location = gs.location 
    AND ds.title_standardized = gti.title_standardized
WHERE gti.market_demand_trend = 'HIGH'
    AND gti.salary_median > 50000
    AND COALESCE(ds.total_jobs, 0) > 3
ORDER BY gs.location, gti.salary_median DESC
LIMIT 30;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. ANALYSE: ENTREPRISES RECRUTEUSES PAR DOMAINE
-- ─────────────────────────────────────────────────────────────────────────────

-- Top 20 entreprises recruteuses de Data Scientists
WITH ds_jobs AS (
    SELECT DISTINCT company 
    FROM silver_jobs 
    WHERE title_standardized = 'Data Scientist' 
    AND is_valid = true
)
SELECT 
    company,
    total_jobs,
    avg_salary_min,
    avg_salary_max
FROM gold_company_stats
WHERE company IN (SELECT * FROM ds_jobs)
ORDER BY total_jobs DESC
LIMIT 20;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. MÉTRIQUES CLÉS (KPIs) POUR DASHBOARD PRINCIPAL
-- ─────────────────────────────────────────────────────────────────────────────

-- Total offres aujourd'hui
SELECT COUNT(*) as total_offres
FROM gold_daily_jobs_snapshot
WHERE snapshot_date = CURRENT_DATE;

-- Nombre d'entreprises uniques
SELECT COUNT(DISTINCT company) as unique_companies
FROM gold_company_stats;

-- Nombre de localités couvertes
SELECT COUNT(DISTINCT location) as unique_locations
FROM gold_location_stats;

-- Salaire moyen global
SELECT 
    ROUND(AVG(salary_median)::numeric, 0) as global_avg_salary,
    ROUND(MIN(salary_median)::numeric, 0) as min_salary,
    ROUND(MAX(salary_median)::numeric, 0) as max_salary
FROM gold_job_title_insights
WHERE salary_median IS NOT NULL;

-- Dashboard résumé unique
SELECT 
    'Total Offres' as metric, COUNT(*)::TEXT as value
FROM gold_daily_jobs_snapshot
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days'

UNION ALL

SELECT 
    'Entreprises Uniques', COUNT(DISTINCT company)::TEXT
FROM gold_company_stats

UNION ALL

SELECT 
    'Localités', COUNT(DISTINCT location)::TEXT
FROM gold_location_stats

UNION ALL

SELECT 
    'Métiers', COUNT(DISTINCT title_standardized)::TEXT
FROM gold_job_title_insights

UNION ALL

SELECT 
    'Salaire Médian Global', ROUND(AVG(salary_median)::numeric, 0)::TEXT
FROM gold_job_title_insights
WHERE salary_median IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. DONNÉES SILVER: REQUÊTES AVANCÉES (pour analyses custom)
-- ─────────────────────────────────────────────────────────────────────────────

-- Tous les Data Scientists valides avec leurs compétences
SELECT 
    title_standardized,
    company,
    location_normalized,
    salary_min,
    salary_max,
    seniority_level,
    keywords,
    job_url
FROM silver_jobs
WHERE title_standardized = 'Data Scientist'
    AND is_valid = true
    AND salary_min IS NOT NULL
ORDER BY salary_max DESC
LIMIT 50;

-- Distribution contrats: CDI vs CDD par métier
SELECT 
    title_standardized,
    contract_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY title_standardized), 2) as pct
FROM silver_jobs
WHERE is_valid = true AND contract_type IS NOT NULL
GROUP BY title_standardized, contract_type
ORDER BY title_standardized, count DESC;

-- Offres avec tous les skillets requises (Python + SQL + Spark + Airflow)
SELECT 
    company,
    title_standardized,
    keywords,
    salary_max,
    location_normalized
FROM silver_jobs
WHERE is_valid = true
    AND keywords @> ARRAY['python', 'sql', 'spark', 'airflow']::TEXT[]
ORDER BY salary_max DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 11. EXPLORATION: TIRER DU BRONZE (pour troubleshooting)
-- ─────────────────────────────────────────────────────────────────────────────

-- Volume par jour et source
SELECT 
    DATE(scraped_at) as date,
    source,
    COUNT(*) as count
FROM jobs
WHERE scraped_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(scraped_at), source
ORDER BY date DESC;

-- Exemple de données brutes (exploration)
SELECT 
    title,
    company,
    location,
    salary,
    source,
    scraped_at
FROM jobs
ORDER BY scraped_at DESC
LIMIT 10;
