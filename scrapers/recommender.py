"""
recommender.py — RECOMMENDER API
─────────────────────────────────────────────────────────────────
FastAPI système de recommandation basé sur CV

Endpoints :
    POST /recommend/cv       → Upload PDF/DOCX → Top-K offres
    POST /recommend/profile  → Profil JSON → Top-K offres
    GET  /health             → Santé de l'API

Lancement :
    uvicorn scrapers.recommender:app --reload --port 8000

Test rapide :
    curl -X POST http://localhost:8000/recommend/cv -F "file=@mon_cv.pdf"

Dépendances (requirements.txt) :
    fastapi>=0.110.0
    uvicorn[standard]
    python-multipart>=0.0.9
    supabase>=2.4.0
    sentence-transformers>=2.7.0
    pdfplumber>=0.10.0
    python-docx>=1.1.0
    spacy>=3.7.0
    langdetect>=1.0.9
    python-dotenv
"""

import os
import math
import logging
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

from scrapers.cv_parser import parse_cv, ParsedCV

load_dotenv()

# ── Config ───────────────────────────────────────────────────────
SUPABASE_URL        = os.environ.get("SUPABASE_API_URL", "")
SUPABASE_KEY        = os.environ.get("SUPABASE_API_KEY", "")
MODEL_NAME          = "paraphrase-multilingual-mpnet-base-v2"

ALPHA_DEFAULT       = 0.7
TOP_K_DEFAULT       = 10
SEMANTIC_CANDIDATES = 50
MAX_FILE_SIZE_MB    = 5
BM25_K1             = 1.5
BM25_B              = 0.75

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Init globale ─────────────────────────────────────────────────
# Lazy load Supabase (don't connect at startup)
supabase: Client = None

def _get_supabase():
    """Lazy load Supabase client on first use"""
    global supabase
    if supabase is None:
        try:
            log.info("Initializing Supabase client...")
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            log.info("✅ Supabase connected")
        except Exception as e:
            log.error(f"❌ Supabase connection failed: {e}")
            supabase = None
    return supabase

# Lazy load model on first use (not at startup)
model = None

def _get_model():
    """Lazy load the SentenceTransformer model on first use"""
    global model
    if model is None:
        try:
            log.info(f"Loading model: {MODEL_NAME} (first request)...")
            model = SentenceTransformer(MODEL_NAME)
            log.info("✅ Model loaded")
        except Exception as e:
            log.error(f"❌ Model loading failed: {e}")
            raise HTTPException(status_code=500, detail=f"Model loading failed: {e}")
    return model

app = FastAPI(
    title       = "Job Recommender API",
    description = "Recommandation d'offres d'emploi par CV",
    version     = "1.0.0",
)


# ── Schémas Pydantic ─────────────────────────────────────────────

class CandidateProfileIn(BaseModel):
    full_name        : Optional[str]  = None
    email            : Optional[str]  = None
    current_title    : Optional[str]  = None
    years_experience : int            = 0
    skills           : list[str]      = Field(default_factory=list)
    languages        : list[str]      = Field(default_factory=list)
    desired_titles   : list[str]      = Field(default_factory=list)
    desired_locations: list[str]      = Field(default_factory=list)


class JobResult(BaseModel):
    job_id          : str
    title           : str
    company         : Optional[str]
    location        : Optional[str]
    contract        : Optional[str]
    skills          : list[str]
    url             : Optional[str]
    score           : float


class CVParseInfo(BaseModel):
    detected_lang    : str
    full_name        : Optional[str]
    current_title    : Optional[str]
    years_experience : int
    skills_found     : list[str]
    languages_found  : list[str]


class RecommendResponse(BaseModel):
    cv_info          : Optional[CVParseInfo]
    total_candidates : int
    recommendations  : list[JobResult]
    generated_at     : str


# ── BM25 Scorer ──────────────────────────────────────────────────

class BM25Scorer:
    def __init__(self, documents: list[str], k1: float = BM25_K1, b: float = BM25_B):
        self.k1    = k1
        self.b     = b
        self.docs  = [d.lower().split() for d in documents]
        self.N     = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / max(self.N, 1)
        self.df    = {}
        for doc in self.docs:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log((self.N - n + 0.5) / (n + 0.5) + 1)

    def score(self, query: str, doc_index: int) -> float:
        tokens = query.lower().split()
        doc    = self.docs[doc_index]
        dl     = len(doc)
        tf_map = {}
        for t in doc:
            tf_map[t] = tf_map.get(t, 0) + 1
        score = 0.0
        for term in tokens:
            tf  = tf_map.get(term, 0)
            idf = self._idf(term)
            num = tf * (self.k1 + 1)
            den = tf + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1))
            score += idf * num / max(den, 1e-6)
        return score

    def score_all(self, query: str) -> list[float]:
        return [self.score(query, i) for i in range(self.N)]


# ── Helpers ──────────────────────────────────────────────────────

def normalize(values: list[float]) -> list[float]:
    if not values:
        return values
    mn, mx = min(values), max(values)
    rng = mx - mn
    if rng == 0:
        return [1.0] * len(values)
    return [(v - mn) / rng for v in values]


def rrf(sem_rank: int, kw_rank: int, alpha: float, k: int = 60) -> float:
    return alpha * (1 / (k + sem_rank)) + (1 - alpha) * (1 / (k + kw_rank))


def job_to_text(job: dict) -> str:
    return " ".join(filter(None, [
        job.get("title", ""),
        " ".join(job.get("keywords") or []),
        job.get("location", ""),
        job.get("contract_type", ""),
    ]))


# ── Moteur de recommandation ─────────────────────────────────────

async def _run_recommendation(
    embedding       : list[float],
    query_text      : str,
    top_k           : int,
    alpha           : float,
) -> dict:
    """Cœur du moteur hybride."""
    sb = _get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not available")

    try:
        # 1. Recherche sémantique via embedding
        resp = sb.rpc("match_jobs", {
            "query_embedding" : embedding,
            "match_threshold" : 0.2,
            "match_count"     : SEMANTIC_CANDIDATES,
        }).execute()
        candidates = resp.data or []
    except Exception as exc:
        log.error(f"Vector search failed: {exc}")
        candidates = []

    if not candidates:
        return {"candidates": [], "total": 0}

    # 2. BM25 keyword scoring
    doc_texts  = [job_to_text(j) for j in candidates]
    bm25       = BM25Scorer(doc_texts)
    bm25_scores = bm25.score_all(query_text)
    sem_scores  = [j.get("similarity", 0.0) for j in candidates]

    sem_norm  = normalize(sem_scores)
    bm25_norm = normalize(bm25_scores)

    # 3. Ranking for RRF
    sem_order  = sorted(range(len(sem_norm)),  key=lambda i: sem_norm[i],  reverse=True)
    bm25_order = sorted(range(len(bm25_norm)), key=lambda i: bm25_norm[i], reverse=True)
    sem_ranks  = [sem_order.index(i) + 1 for i in range(len(candidates))]
    bm25_ranks = [bm25_order.index(i) + 1 for i in range(len(candidates))]

    # 4. Score fusion
    scored = []
    for idx, job in enumerate(candidates):
        scored.append({
            **job,
            "semantic_score" : round(sem_norm[idx], 4),
            "keyword_score"  : round(bm25_norm[idx], 4),
            "final_score"    : round(rrf(sem_ranks[idx], bm25_ranks[idx], alpha), 6),
        })

    # 5. Sort and Top-K
    scored.sort(key=lambda j: j["final_score"], reverse=True)
    top_jobs = scored[:top_k]

    return {"candidates": top_jobs, "total": len(candidates)}


def _build_response(
    result       : dict,
    cv_info      : Optional[CVParseInfo],
) -> RecommendResponse:
    return RecommendResponse(
        cv_info          = cv_info,
        total_candidates = result["total"],
        recommendations  = [
            JobResult(
                job_id  = j.get("job_id", ""),
                title   = j.get("title", ""),
                company = j.get("company"),
                location= j.get("location_normalized"),
                contract= j.get("contract_type"),
                skills  = j.get("keywords") or [],
                url     = j.get("job_url"),
                score   = j["final_score"],
            )
            for j in result["candidates"]
        ],
        generated_at = datetime.now(timezone.utc).isoformat(),
    )


# ── Routes ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status"    : "ok",
        "timestamp" : datetime.now(timezone.utc).isoformat(),
        "note"      : "API is ready. Model and Supabase load on first recommendation."
    }


@app.post("/recommend/cv", response_model=RecommendResponse)
async def recommend_from_cv(
    file            : UploadFile = File(...),
    top_k           : int        = Query(TOP_K_DEFAULT, ge=1, le=50),
    alpha           : float      = Query(ALPHA_DEFAULT, ge=0.0, le=1.0),
):
    """Upload CV and get top job offers."""
    filename = file.filename or "cv"
    if not filename.lower().endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(status_code=415, detail="Supported formats: PDF, DOCX")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Max size: {MAX_FILE_SIZE_MB} MB")

    # Parse CV
    parsed: ParsedCV = parse_cv(file_bytes, filename)
    if not parsed.profile_summary:
        raise HTTPException(status_code=422, detail="CV parsing failed")

    # Embed candidate (lazy load model)
    embedding = _get_model().encode(
        parsed.profile_summary,
        normalize_embeddings=True,
    ).tolist()

    # Query text for BM25
    query_text = " ".join(filter(None, [
        parsed.current_title or "",
        " ".join(parsed.skills),
    ]))

    # Get recommendations
    result = await _run_recommendation(
        embedding   = embedding,
        query_text  = query_text,
        top_k       = top_k,
        alpha       = alpha,
    )

    cv_info = CVParseInfo(
        detected_lang    = parsed.detected_lang,
        full_name        = parsed.full_name,
        current_title    = parsed.current_title,
        years_experience = parsed.years_experience,
        skills_found     = parsed.skills,
        languages_found  = parsed.languages,
    )

    return _build_response(result, cv_info)


@app.post("/recommend/profile", response_model=RecommendResponse)
async def recommend_from_profile(
    profile         : CandidateProfileIn,
    top_k           : int   = Query(TOP_K_DEFAULT, ge=1, le=50),
    alpha           : float = Query(ALPHA_DEFAULT, ge=0.0, le=1.0),
):
    """Profile-based recommendation (without CV)."""
    parts = []
    if profile.current_title:
        parts.append(profile.current_title)
    if profile.desired_titles:
        parts.append("Recherche : " + ", ".join(profile.desired_titles))
    if profile.skills:
        parts.append("Compétences : " + ", ".join(profile.skills))
    if profile.desired_locations:
        parts.append("Lieu : " + ", ".join(profile.desired_locations))

    profile_text = " | ".join(parts)
    embedding    = _get_model().encode(profile_text, normalize_embeddings=True).tolist()
    query_text   = " ".join(filter(None, [
        profile.current_title or "",
        " ".join(profile.skills),
    ]))

    result = await _run_recommendation(
        embedding   = embedding,
        query_text  = query_text,
        top_k       = top_k,
        alpha       = alpha,
    )

    return _build_response(result, None)
