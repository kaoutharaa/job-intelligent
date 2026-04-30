"""
Job Intelligent — FastAPI REST API
Exposes gold_jobs table for NLP recommendation system and frontend use.

Run locally:
    pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas
    uvicorn api:app --reload --port 8000

Docker: already included in docker-compose.yml
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from typing import Optional
import pandas as pd
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import File, Form, UploadFile
import PyPDF2
import io

# ─── CONFIG ────────────────────────────────────────────────────────────────────

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER', 'admin')}:"
    f"{os.getenv('DB_PASS', 'password')}@"
    f"{os.getenv('DB_HOST', 'postgres')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'job_intelligent')}"
)

engine = create_engine(DB_URL)

# ─── APP ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Job Intelligent API",
    description="REST API for the Job Intelligent NLP recommendation system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def query_df(sql: str, params: dict = None) -> pd.DataFrame:
    if params is None:
        params = {}
    with engine.connect() as conn:
        # We bypass pandas' broken SQL reader and let SQLAlchemy do the work safely
        result = conn.execute(text(sql), params)
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def df_to_records(df: pd.DataFrame) -> list:
    return df.where(pd.notnull(df), None).to_dict(orient="records")

# =============================================================================
# ENDPOINTS
# =============================================================================

# ─── HEALTH ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "api": "Job Intelligent", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

# ─── JOBS ──────────────────────────────────────────────────────────────────────

@app.get("/jobs", tags=["Jobs"])
def get_jobs(
    source:   Optional[str] = Query(None, description="Filter by source: linkedin / france_travail"),
    category: Optional[str] = Query(None, description="Filter by category: Data & AI / DevOps & Cloud / etc."),
    location: Optional[str] = Query(None, description="Filter by city"),
    title:    Optional[str] = Query(None, description="Search in job title"),
    limit:    int           = Query(50,   description="Number of results", le=500),
    offset:   int           = Query(0,    description="Pagination offset"),
):
    """
    Get jobs from the gold layer with optional filters.
    Used by the NLP system to fetch candidate jobs for matching.
    """
    conditions = ["1=1"]
    params     = {}

    if source:
        conditions.append("source = :source")
        params["source"] = source

    if category:
        conditions.append("category = :category")
        params["category"] = category

    if location:
        conditions.append("LOWER(location) LIKE :location")
        params["location"] = f"%{location.lower()}%"

    if title:
        conditions.append("LOWER(title) LIKE :title")
        params["title"] = f"%{title.lower()}%"

    where = " AND ".join(conditions)

    sql = f"""
        SELECT *
        FROM gold_jobs
        WHERE {where}
        ORDER BY date_posted DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """
    params["limit"]  = limit
    params["offset"] = offset

    df = query_df(sql, params)
    return {
        "total":  len(df),
        "offset": offset,
        "limit":  limit,
        "jobs":   df_to_records(df),
    }


@app.get("/jobs/{job_id}", tags=["Jobs"])
def get_job(job_id: int):
    """Get a single job by ID."""
    df = query_df("SELECT * FROM gold_jobs WHERE id = :id", {"id": job_id})
    if df.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    return df_to_records(df)[0]


@app.get("/jobs/search/{keyword}", tags=["Jobs"])
def search_jobs(
    keyword: str,
    limit:   int = Query(20, le=200),
):
    """
    Full-text search across title, company, skills and location.
    Main endpoint for the NLP recommendation system.
    """
    sql = """
        SELECT *,
               ts_rank(
                   to_tsvector('french', COALESCE(title,'') || ' ' ||
                               COALESCE(company,'') || ' ' ||
                               COALESCE(skills,'') || ' ' ||
                               COALESCE(location,'')),
                   plainto_tsquery('french', :keyword)
               ) AS rank
        FROM gold_jobs
        WHERE
            to_tsvector('french', COALESCE(title,'') || ' ' ||
                        COALESCE(company,'') || ' ' ||
                        COALESCE(skills,'') || ' ' ||
                        COALESCE(location,''))
            @@ plainto_tsquery('french', :keyword)
        ORDER BY rank DESC
        LIMIT :limit
    """
    df = query_df(sql, {"keyword": keyword, "limit": limit})
    return {
        "keyword": keyword,
        "total":   len(df),
        "jobs":    df_to_records(df),
    }

# ─── STATS ─────────────────────────────────────────────────────────────────────

@app.get("/stats", tags=["Stats"])
def get_stats():
    """
    Global statistics for Power BI dashboard and monitoring.
    Returns counts by source, category, location and top skills.
    """
    with engine.connect() as conn:
        total    = conn.execute(text("SELECT COUNT(*) FROM gold_jobs")).scalar()
        by_src   = conn.execute(text("SELECT source, COUNT(*) as count FROM gold_jobs GROUP BY source ORDER BY count DESC")).fetchall()
        by_cat   = conn.execute(text("SELECT category, COUNT(*) as count FROM gold_jobs GROUP BY category ORDER BY count DESC")).fetchall()
        by_loc   = conn.execute(text("SELECT location, COUNT(*) as count FROM gold_jobs GROUP BY location ORDER BY count DESC LIMIT 10")).fetchall()
        by_title = conn.execute(text("SELECT title, COUNT(*) as count FROM gold_jobs GROUP BY title ORDER BY count DESC LIMIT 10")).fetchall()

    return {
        "total_jobs":       total,
        "by_source":        [{"source": r[0], "count": r[1]} for r in by_src],
        "by_category":      [{"category": r[0], "count": r[1]} for r in by_cat],
        "top_locations":    [{"location": r[0], "count": r[1]} for r in by_loc],
        "top_titles":       [{"title": r[0], "count": r[1]} for r in by_title],
    }


@app.get("/stats/skills", tags=["Stats"])
def get_top_skills(limit: int = Query(20, le=100)):
    """
    Get the most in-demand skills across all job listings.
    Useful for the Power BI skills demand chart.
    """
    df = query_df(
        "SELECT skills FROM gold_jobs WHERE skills IS NOT NULL AND skills != ''"
    )

    if df.empty:
        return {"skills": []}

    from collections import Counter
    all_skills = []
    for row in df["skills"]:
        if row:
            all_skills.extend([s.strip() for s in row.split(",")])

    top = Counter(all_skills).most_common(limit)
    return {
        "total_unique_skills": len(set(all_skills)),
        "skills": [{"skill": s, "count": c} for s, c in top],
    }


@app.get("/stats/timeline", tags=["Stats"])
def get_timeline():
    """
    Job posting count by date — for time series charts in Power BI.
    """
    df = query_df("""
        SELECT
            date_posted,
            COUNT(*) as count,
            source
        FROM gold_jobs
        WHERE date_posted IS NOT NULL
        GROUP BY date_posted, source
        ORDER BY date_posted DESC
        LIMIT 90
    """)
    return {"timeline": df_to_records(df)}

# ─── MEDALLION LAYER STATS ─────────────────────────────────────────────────────

@app.get("/layers", tags=["Medallion"])
def get_layer_stats():
    """
    Row counts for all medallion layers — useful for monitoring.
    """
    tables = [
        "bronze_linkedin",
        "bronze_france_travail",
        "silver_linkedin",
        "silver_france_travail",
        "gold_jobs",
    ]
    result = {}
    with engine.connect() as conn:
        for table in tables:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                result[table] = count
            except Exception:
                result[table] = "not found"

    return {"layers": result}

# ─── NLP ENDPOINTS ─────────────────────────────────────────────────────────────

@app.post("/recommend", tags=["NLP"])
async def recommend_jobs(
    limit: int = Query(10, le=50),
    title: str = Form(""),
    location: str = Form(""),
    cv: UploadFile = File(None),
    user_id: Optional[int] = Form(None) # Nouveau paramètre
):
    """
    Recommend jobs using TF-IDF.
    Extracts text directly from the uploaded CV for semantic matching.
    """
    sql = "SELECT * FROM gold_jobs WHERE 1=1"
    params = {}
    if location:
        sql += " AND LOWER(location) LIKE :location"
        params["location"] = f"%{location.lower()}%"
        
    df_jobs = query_df(sql, params)
    if df_jobs.empty:
        return {"total_found": 0, "jobs": []}

    cv_text = ""
    if cv and cv.filename.endswith('.pdf'):
        try:
            pdf_content = await cv.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    cv_text += extracted + " "
        except Exception as e:
            print(f"Error reading PDF: {e}")

    df_jobs['nlp_text'] = (
        df_jobs['title'].fillna('') + " " + 
        df_jobs['skills'].fillna('') + " " + 
        df_jobs['category'].fillna('')
    ).str.lower()
    
    user_text = f"{title} {cv_text}".lower()
    
    vectorizer = TfidfVectorizer()
    all_texts = df_jobs['nlp_text'].tolist() + [user_text]
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    user_vector = tfidf_matrix[-1]
    job_vectors = tfidf_matrix[:-1]
    similarities = cosine_similarity(user_vector, job_vectors)[0]
    
    df_jobs['score'] = (similarities * 100).round(1)
    matched_jobs = df_jobs[df_jobs['score'] > 0].sort_values(by='score', ascending=False).head(limit)
    matched_jobs = matched_jobs.drop(columns=['nlp_text'])

    # Formatage des résultats en liste de dictionnaires
    results_list = df_to_records(matched_jobs)

    # ─── SAUVEGARDE EN BASE DE DONNÉES ───
    if user_id:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO user_analyses (user_id, profile_data, jobs_results)
                        VALUES (:user_id, :profile_data, :jobs_results)
                    """),
                    {
                        "user_id": user_id,
                        "profile_data": json.dumps({"titre": title, "ville": location}),
                        "jobs_results": json.dumps(results_list)
                    }
                )
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de l'analyse : {e}")

    return {
        "total_found": len(matched_jobs),
        "jobs": results_list,
    }


@app.get("/categories", tags=["NLP"])
def get_categories():
    """List all available job categories — useful for NLP classification."""
    df = query_df(
        "SELECT DISTINCT category FROM gold_jobs WHERE category IS NOT NULL ORDER BY category"
    )
    return {"categories": df["category"].tolist()}


@app.get("/titles", tags=["NLP"])
def get_standardized_titles():
    """List all standardized job titles — useful for NLP model training."""
    df = query_df(
        "SELECT DISTINCT title, COUNT(*) as count FROM gold_jobs GROUP BY title ORDER BY count DESC"
    )
    return {"titles": df_to_records(df)}


import hashlib
import secrets
import json
from pydantic import BaseModel

# ─── SÉCURITÉ ET MODÈLES D'AUTH ────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    # Utilisation de pbkdf2_hmac pour un hachage hautement sécurisé
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return f"{salt}:{pwd_hash.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    salt, hash_hex = hashed.split(':')
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return pwd_hash.hex() == hash_hex

class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str



# ─── AUTHENTIFICATION & UTILISATEURS ───────────────────────────────────────────

@app.post("/register", tags=["Auth"])
def register_user(req: RegisterRequest):
    hashed_pw = hash_password(req.password)
    try:
        # engine.begin() s'assure que la transaction est bien sauvegardée (commit)
        with engine.begin() as conn:
            # Vérifier si l'email existe déjà
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email"), 
                {"email": req.email}
            ).fetchone()
            
            if existing:
                raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

            # Insérer le nouvel utilisateur
            result = conn.execute(
                text("""
                    INSERT INTO users (first_name, last_name, email, password_hash)
                    VALUES (:first_name, :last_name, :email, :password_hash)
                    RETURNING id, first_name, last_name, email
                """),
                {
                    "first_name": req.firstName,
                    "last_name": req.lastName,
                    "email": req.email,
                    "password_hash": hashed_pw
                }
            )
            user = result.fetchone()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Erreur base de données.")

    return {"user": {"id": user.id, "firstName": user.first_name, "lastName": user.last_name, "email": user.email}}


@app.post("/login", tags=["Auth"])
def login_user(req: LoginRequest):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id, first_name, last_name, email, password_hash FROM users WHERE email = :email"),
            {"email": req.email}
        ).fetchone()

    # Vérification du mot de passe
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    return {"user": {"id": user.id, "firstName": user.first_name, "lastName": user.last_name, "email": user.email}}


@app.get("/analysis/{user_id}", tags=["Auth"])
def get_user_analysis(user_id: int):
    with engine.connect() as conn:
        # Récupère l'analyse la plus récente pour cet utilisateur
        analysis = conn.execute(
            text("SELECT profile_data, jobs_results FROM user_analyses WHERE user_id = :user_id ORDER BY created_at DESC LIMIT 1"),
            {"user_id": user_id}
        ).fetchone()

    if not analysis:
        raise HTTPException(status_code=404, detail="Aucune analyse trouvée.")

    return {
        "profile": json.loads(analysis.profile_data) if isinstance(analysis.profile_data, str) else analysis.profile_data,
        "jobs": json.loads(analysis.jobs_results) if isinstance(analysis.jobs_results, str) else analysis.jobs_results
    }