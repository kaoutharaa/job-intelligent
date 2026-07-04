"""
Job Intelligent — FastAPI REST API
Exposes gold_jobs table for NLP recommendation system and frontend use.

Run locally:
    pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas
    uvicorn api:app --reload --port 8000

Docker: already included in docker-compose.yml
"""

from fastapi import FastAPI, Query, HTTPException, Depends, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, text
from typing import Optional
from datetime import datetime, timezone, timedelta
import pandas as pd
import os
import io
import json
import hashlib
import secrets
import logging
import threading
import jwt
import PyPDF2
from pydantic import BaseModel, EmailStr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger("job_intelligent.api")

# ─── CONFIG ────────────────────────────────────────────────────────────────────

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER', 'admin')}:"
    f"{os.getenv('DB_PASS', 'password')}@"
    f"{os.getenv('DB_HOST', 'postgres')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'job_intelligent')}"
)

engine = create_engine(DB_URL, pool_pre_ping=True)

# ─── AUTH CONFIG ───────────────────────────────────────────────────────────────

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Fall back to an ephemeral secret so local dev still works, but warn loudly:
    # tokens are invalidated on every restart and this is NOT safe for production.
    JWT_SECRET = secrets.token_hex(32)
    log.warning(
        "JWT_SECRET is not set — using a random ephemeral secret. "
        "Set JWT_SECRET in the environment for stable, production-safe tokens."
    )

# Comma-separated list of allowed frontend origins.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

# ─── APP ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Job Intelligent API",
    description="REST API for the Job Intelligent NLP recommendation system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
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

# ─── SECURITY: PASSWORD HASHING ─────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000)
    return f"{salt}:{pwd_hash.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, hash_hex = hashed.split(":")
    except (ValueError, AttributeError):
        return False
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000)
    # Constant-time comparison to avoid timing attacks.
    return secrets.compare_digest(pwd_hash.hex(), hash_hex)

# ─── SECURITY: JWT TOKENS ───────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Return the user id encoded in a valid token, or raise 401."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> int:
    """Require a valid bearer token; returns the authenticated user id."""
    if creds is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return decode_access_token(creds.credentials)


def get_optional_user_id(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[int]:
    """Return the authenticated user id if a valid token is present, else None."""
    if creds is None:
        return None
    return decode_access_token(creds.credentials)

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

    # Total matching rows (ignores pagination) so the frontend can page correctly.
    total = query_df(
        f"SELECT COUNT(*) AS n FROM gold_jobs WHERE {where}", params
    )["n"].iloc[0]

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
        "total":    int(total),
        "returned": len(df),
        "offset":   offset,
        "limit":    limit,
        "jobs":     df_to_records(df),
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

class _JobIndex:
    """
    Caches the fitted TF-IDF corpus over all gold_jobs so /recommend does not
    refit the vectorizer on every request. Rebuilt only when the gold_jobs row
    count changes (e.g. after the ETL replaces the table).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._rowcount = None
        self._df = None
        self._matrix = None
        self._vectorizer = None

    def get(self):
        with engine.connect() as conn:
            rowcount = conn.execute(text("SELECT COUNT(*) FROM gold_jobs")).scalar()

        with self._lock:
            if self._rowcount == rowcount and self._df is not None:
                return self._df, self._matrix, self._vectorizer

            df = query_df("SELECT * FROM gold_jobs")
            if df.empty:
                self._rowcount = rowcount
                self._df, self._matrix, self._vectorizer = df, None, None
                return df, None, None

            nlp_text = (
                df["title"].fillna("") + " "
                + df["skills"].fillna("") + " "
                + df["category"].fillna("")
            ).str.lower()

            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(nlp_text.tolist())

            self._rowcount = rowcount
            self._df, self._matrix, self._vectorizer = df, matrix, vectorizer
            return df, matrix, vectorizer


_job_index = _JobIndex()


@app.post("/recommend", tags=["NLP"])
async def recommend_jobs(
    limit: int = Query(10, le=50),
    title: str = Form(""),
    location: str = Form(""),
    cv: UploadFile = File(None),
    user_id: Optional[int] = Depends(get_optional_user_id),
):
    """
    Recommend jobs using TF-IDF over a cached corpus.
    Extracts text directly from the uploaded CV for semantic matching.
    If the caller is authenticated, the analysis is saved to their history.
    """
    title = title.strip()
    location = location.strip()

    df_all, matrix, vectorizer = _job_index.get()
    if df_all is None or df_all.empty or vectorizer is None:
        return {"total_found": 0, "jobs": []}

    cv_text = ""
    if cv and cv.filename and cv.filename.lower().endswith(".pdf"):
        try:
            pdf_content = await cv.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    cv_text += extracted + " "
        except Exception as e:
            log.warning(f"Failed to read uploaded CV PDF: {e}")

    user_text = f"{title} {cv_text}".lower()

    # Score the whole corpus against the user, then apply text filters in pandas.
    user_vector = vectorizer.transform([user_text])
    similarities = cosine_similarity(user_vector, matrix)[0]

    df_jobs = df_all.copy()
    df_jobs["score"] = (similarities * 100).round(1)

    # Filter: every title term must appear in title or title_raw; location LIKE.
    haystack = (
        df_jobs["title"].fillna("") + " " + df_jobs.get("title_raw", "").fillna("")
    ).str.lower()
    for term in [t for t in title.lower().split() if t]:
        df_jobs = df_jobs[haystack.loc[df_jobs.index].str.contains(term, regex=False)]
    if location:
        df_jobs = df_jobs[
            df_jobs["location"].fillna("").str.lower().str.contains(location.lower(), regex=False)
        ]

    matched_jobs = (
        df_jobs[df_jobs["score"] > 0]
        .sort_values(by="score", ascending=False)
        .head(limit)
    )
    results_list = df_to_records(matched_jobs)

    # ─── Save to history (only for authenticated users) ───
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
                        # default=str handles non-JSON types like date_posted (datetime.date).
                        "jobs_results": json.dumps(results_list, default=str),
                    },
                )
        except Exception as e:
            log.error(f"Failed to save analysis for user {user_id}: {e}")

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


# ─── AUTH MODELS ───────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _auth_response(user) -> dict:
    """Build the standard auth payload: a bearer token plus public user fields."""
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
        },
    }

# ─── AUTHENTIFICATION & UTILISATEURS ───────────────────────────────────────────

@app.post("/register", tags=["Auth"])
def register_user(req: RegisterRequest):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères.")
    hashed_pw = hash_password(req.password)
    try:
        with engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": req.email},
            ).fetchone()

            if existing:
                raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

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
                    "password_hash": hashed_pw,
                },
            )
            user = result.fetchone()
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Registration DB error: {e}")
        raise HTTPException(status_code=500, detail="Erreur base de données.")

    return _auth_response(user)


@app.post("/login", tags=["Auth"])
def login_user(req: LoginRequest):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id, first_name, last_name, email, password_hash FROM users WHERE email = :email"),
            {"email": req.email},
        ).fetchone()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    return _auth_response(user)


@app.get("/analysis/me", tags=["Auth"])
def get_my_analysis(user_id: int = Depends(get_current_user_id)):
    """Return the caller's most recent saved analysis (derived from the token)."""
    with engine.connect() as conn:
        analysis = conn.execute(
            text("SELECT profile_data, jobs_results FROM user_analyses WHERE user_id = :user_id ORDER BY created_at DESC LIMIT 1"),
            {"user_id": user_id},
        ).fetchone()

    if not analysis:
        raise HTTPException(status_code=404, detail="Aucune analyse trouvée.")

    return {
        "profile": json.loads(analysis.profile_data) if isinstance(analysis.profile_data, str) else analysis.profile_data,
        "jobs": json.loads(analysis.jobs_results) if isinstance(analysis.jobs_results, str) else analysis.jobs_results,
    }