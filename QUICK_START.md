# ✅ RECOMMENDATION SYSTEM - COMPLETE SETUP

## 🎯 What Was Created

Your complete job recommendation system is now ready! Here's what was generated:

---

## 📁 New Files Created

### Core Application Files

| File | Purpose |
|------|---------|
| **scrapers/cv_parser.py** | CV parsing engine - extracts skills, experience, titles from PDF/DOCX |
| **scrapers/embed_pipeline.py** | Embedding generator - creates vector representations for jobs & candidates |
| **scrapers/recommender.py** | FastAPI backend - the main recommendation API with 2 endpoints |

### Database & Setup

| File | Purpose |
|------|---------|
| **sql/recommender_schema.sql** | Database tables: candidate_profiles, recommendation_logs, match_jobs function |
| **requirements.txt** | Updated with all recommender dependencies (cleaned duplicates) |

### Frontend & Documentation

| File | Purpose |
|------|---------|
| **index.html** | Beautiful web UI for CV upload & job recommendations |
| **RECOMMENDER_README.md** | Complete guide (architecture, API docs, tuning, troubleshooting) |
| **recommender_setup.sh** | Linux/Mac setup script |
| **recommender_setup.bat** | Windows setup script |
| **QUICK_START.md** | This file - quick reference |

---

## 🚀 Quick Start (5 minutes)

### 1️⃣ Install Dependencies

```bash
# Windows
recommender_setup.bat

# Or manually
pip install -r requirements.txt
python -m spacy download fr_core_news_md
python -m spacy download en_core_web_md
```

### 2️⃣ Start the API

```bash
uvicorn scrapers.recommender:app --reload --port 8000
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
Press CTRL+C to quit
```

### 3️⃣ Test the System

**Option A: Web Interface**
- Open `index.html` in your browser
- Drag & drop your CV
- Click "Trouver les meilleures offres"

**Option B: API Test**
```bash
curl -X POST http://localhost:8000/recommend/cv \
  -F "file=@your_cv.pdf" \
  -F "top_k=10"
```

**Option C: Swagger UI**
- Visit http://localhost:8000/docs
- Test endpoints interactively

---

## 🏗️ Architecture

```
User CV (PDF/DOCX)
    ↓
1. CV PARSER (cv_parser.py)
   - Extract: title, skills, experience, languages
   - Detect: language (FR/EN)
    ↓
2. EMBEDDING (recommender.py)
   - SentenceTransformer model (768-dim vector)
    ↓
3. SEARCH (Supabase pgvector)
   - Semantic search: ~50 similar jobs
   - BM25 keyword scoring
   - RRF ranking (Reciprocal Rank Fusion)
    ↓
4. RESULTS
   - Top-K recommendations with scores (0-1)
   - Return job title, company, skills, URL

```

---

## 📡 API Endpoints

### POST /recommend/cv
Upload CV and get recommendations.

```bash
curl -X POST http://localhost:8000/recommend/cv \
  -F "file=@cv.pdf" \
  -F "top_k=10" \
  -F "alpha=0.7"
```

**Response:**
```json
{
  "cv_info": {
    "detected_lang": "fr",
    "full_name": "Jean Dupont",
    "current_title": "Data Engineer",
    "years_experience": 5,
    "skills_found": ["Python", "SQL", "Spark"],
    "languages_found": ["Français", "Anglais"]
  },
  "total_candidates": 120,
  "recommendations": [
    {
      "job_id": "abc123",
      "title": "Senior Data Engineer",
      "company": "TechCorp",
      "location": "Paris",
      "contract": "CDI",
      "skills": ["Python", "Spark", "AWS"],
      "url": "https://...",
      "score": 0.89
    }
  ]
}
```

### POST /recommend/profile
Recommend without CV (JSON profile).

```bash
curl -X POST http://localhost:8000/recommend/profile \
  -H "Content-Type: application/json" \
  -d '{
    "current_title": "Data Analyst",
    "skills": ["Python", "Excel"],
    "years_experience": 3
  }'
```

### GET /health
Check API status.

```bash
curl http://localhost:8000/health
# {"status":"ok","timestamp":"2026-04-19T..."}
```

---

## ⚙️ How to Configure

### Parameters

| Parameter | Type | Default | Range | Effect |
|-----------|------|---------|-------|--------|
| `file` | File | required | PDF/DOCX | CV to analyze |
| `top_k` | int | 10 | 1-50 | Number of results |
| `alpha` | float | 0.7 | 0-1 | Semantic weight (1.0=semantic, 0.0=keywords) |

### Example: Keyword-focused Search
```bash
# alpha=0 → prioritize keywords (good for exact skill matching)
curl -X POST http://localhost:8000/recommend/cv \
  -F "file=@cv.pdf" \
  -F "alpha=0.3"
```

### Example: Semantic-focused Search
```bash
# alpha=1 → prioritize semantic similarity (good for career changes)
curl -X POST http://localhost:8000/recommend/cv \
  -F "file=@cv.pdf" \
  -F "alpha=0.9"
```

---

## 🔧 Database Setup

### Required: pgvector Extension

```sql
-- In your Supabase SQL editor
CREATE EXTENSION vector;
```

### Tables Created

```sql
-- 1. For recommendations
CREATE TABLE candidate_profiles (
    id, full_name, skills[], languages[],
    embedding VECTOR(768), ...
);

-- 2. For logging
CREATE TABLE recommendation_logs (
    candidate_id, job_id, scores[], ...
);

-- 3. Updated silver_jobs
ALTER TABLE silver_jobs ADD COLUMN embedding VECTOR(768);
```

### Function for Search

```sql
CREATE FUNCTION match_jobs(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.2,
    match_count INT DEFAULT 50
)
-- Returns: job_id, title, company, similarity, ...
```

---

## 📊 Embedding Pipeline

To get embeddings for your job offers:

### Option 1: Airflow Integration
Add to your DAG:
```python
from scrapers.embed_pipeline import embed_task

embed_jobs = PythonOperator(
    task_id="embed_jobs",
    python_callable=embed_task,
    execution_timeout=timedelta(hours=3),
)
```

### Option 2: Manual Run
```python
from scrapers.embed_pipeline import EmbedPipeline
pipeline = EmbedPipeline()
count = pipeline.embed_jobs_batch(batch_size=50)
print(f"Embedded {count} jobs")
```

### Option 3: One-liner
```bash
python -c "from scrapers.embed_pipeline import embed_task; print(embed_task())"
```

---

## 🐛 Troubleshooting

### Error: "Service not available"
```
→ API not running or Supabase not connected
→ Check: uvicorn running, .env vars set, Supabase online
```

### Error: "Vector search failed"
```
→ pgvector not enabled or silver_jobs has no embeddings
→ Fix: CREATE EXTENSION vector; and run embedding pipeline
```

### Error: "CV parsing failed"
```
→ File not PDF/DOCX, or corrupted
→ Fix: Use valid PDF or DOCX file
```

### Slow Embeddings
```
→ Normal: First run loads large model (~400MB)
→ Subsequent runs are faster (cached)
→ GPU not used: That's OK, CPU works fine
```

---

## 📈 Performance Tips

1. **Faster API:**
   - Increase batch size in embed_pipeline.py
   - Increase match_threshold in recommender.py

2. **Better Results:**
   - Lower alpha for exact skill matching (alpha=0.3)
   - Raise alpha for fuzzy matching (alpha=0.9)
   - Increase top_k for more options

3. **Database:**
   - Create index on silver_jobs.embedding
   - Archive old recommendation_logs
   - Monitor pgvector index size

---

## 📚 File Structure

```
Projet/
├── scrapers/
│   ├── cv_parser.py          ← CV parsing
│   ├── embed_pipeline.py     ← Embeddings
│   ├── recommender.py        ← API backend
│   └── ... (other modules)
├── sql/
│   ├── medallion_schema.sql  (updated)
│   └── recommender_schema.sql (new)
├── index.html                ← Web UI
├── requirements.txt          (updated)
├── RECOMMENDER_README.md     ← Full docs
├── QUICK_START.md            ← This file
├── recommender_setup.bat     ← Windows setup
└── recommender_setup.sh      ← Linux setup
```

---

## ✨ Features Included

✅ CV parsing (PDF + DOCX)
✅ Multi-language support (FR, EN, AR)
✅ Semantic search (pgvector)
✅ Keyword search (BM25)
✅ Hybrid ranking (RRF)
✅ Beautiful web UI
✅ FastAPI with Swagger docs
✅ Batch embedding pipeline
✅ Production-ready error handling
✅ Comprehensive logging

---

## 🎓 Next Steps

1. **Deploy:**
   - Test locally with sample CVs
   - Deploy API to production (AWS, Heroku, etc.)
   - Deploy frontend to web server

2. **Optimize:**
   - A/B test different alpha values
   - Analyze recommendation quality metrics
   - Tune BM25 parameters

3. **Scale:**
   - Run embedding pipeline on schedule (Airflow)
   - Archive old logs
   - Monitor API performance

4. **Enhance:**
   - Add user feedback (thumbs up/down)
   - Train custom ranking model
   - Mobile app for candidates

---

## 📞 Quick Help

| Need Help With? | See |
|-----------------|-----|
| API Usage | http://localhost:8000/docs |
| Full Documentation | RECOMMENDER_README.md |
| Database Setup | sql/recommender_schema.sql |
| CV Parser Details | scrapers/cv_parser.py |
| API Details | scrapers/recommender.py |
| Web UI Features | index.html |

---

## 🎉 You're All Set!

Your job recommendation system is ready to use. Start the API and try it out!

```bash
# Terminal 1: Start API
uvicorn scrapers.recommender:app --reload --port 8000

# Terminal 2: Open index.html in browser
# Or test via curl
```

**Happy recommending! 🚀**

---

*Generated: April 19, 2026*
*Version: 1.0.0*
