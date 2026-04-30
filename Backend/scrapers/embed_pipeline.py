"""
embed_pipeline.py  — VERSION CORRIGÉE (update par job_id)
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_API_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_API_KEY", "")
MODEL_NAME   = "paraphrase-multilingual-mpnet-base-v2"

supabase_client: Optional[Client] = None
_model = None

def _init():
    global supabase_client, _model
    if supabase_client is None:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    if _model is None:
        from sentence_transformers import SentenceTransformer
        log.info(f"Chargement du modele {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
        log.info("Modele charge.")


class EmbedPipeline:

    def __init__(self):
        _init()
        self.model    = _model
        self.supabase = supabase_client

    def _job_to_text(self, job: Dict[str, Any]) -> str:
        parts = []
        if job.get("title"):
            parts.append(job["title"])
        if job.get("company"):
            parts.append(f"chez {job['company']}")
        keywords = job.get("keywords") or []
        if isinstance(keywords, list) and keywords:
            parts.append("Competences : " + ", ".join(str(k) for k in keywords[:10]))
        if job.get("location_normalized"):
            parts.append(f"a {job['location_normalized']}")
        elif job.get("location"):
            parts.append(f"a {job['location']}")
        if job.get("contract_type"):
            parts.append(job["contract_type"])
        return " | ".join(parts)

    def embed_jobs_batch(self, batch_size: int = 50) -> int:
        log.info("Demarrage embedding des offres...")

        resp = (
            self.supabase.table("silver_jobs")
            .select("job_id, title, company, location_normalized, contract_type, keywords")
            .is_("embedding", "null")
            .limit(1000)
            .execute()
        )
        jobs = resp.data or []

        if not jobs:
            log.info("Aucune offre a traiter.")
            return 0

        log.info(f"Traitement de {len(jobs)} offres (batch={batch_size})...")
        processed = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            texts = [self._job_to_text(j) for j in batch]

            try:
                embeddings = self.model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                ).tolist()

                # UPDATE individuel par job_id (evite les contraintes NOT NULL)
                for job, emb in zip(batch, embeddings):
                    self.supabase.table("silver_jobs").update({
                        "embedding"   : emb,
                        "embedded_at" : now_iso,
                    }).eq("job_id", job["job_id"]).execute()

                processed += len(batch)
                log.info(f"  Lot {i//batch_size + 1} : {processed}/{len(jobs)} offres traitees")

            except Exception as exc:
                log.error(f"Erreur lot {i//batch_size + 1} : {exc}")
                break

        log.info(f"Termine — {processed} offres embeddees.")
        return processed

    def embed_candidate(self, candidate_id: str) -> bool:
        try:
            resp = (
                self.supabase.table("candidate_profiles")
                .select("*")
                .eq("id", candidate_id)
                .single()
                .execute()
            )
            candidate = resp.data
            if not candidate:
                log.warning(f"Candidat {candidate_id} introuvable")
                return False

            parts = []
            if candidate.get("current_title"):
                parts.append(candidate["current_title"])
            if candidate.get("skills"):
                parts.append("Competences : " + ", ".join(candidate["skills"]))
            if candidate.get("profile_summary"):
                parts.append(candidate["profile_summary"])
            text      = " | ".join(parts)
            embedding = self.model.encode(text, normalize_embeddings=True).tolist()

            self.supabase.table("candidate_profiles").update({
                "embedding"   : embedding,
                "embedded_at" : datetime.now(timezone.utc).isoformat(),
            }).eq("id", candidate_id).execute()

            log.info(f"Embedding candidat {candidate_id} genere.")
            return True

        except Exception as exc:
            log.error(f"Erreur candidat {candidate_id} : {exc}")
            return False


def embed_task() -> int:
    pipeline = EmbedPipeline()
    total = 0
    while True:
        n = pipeline.embed_jobs_batch(batch_size=50)
        total += n
        if n == 0:
            break
    return total


if __name__ == "__main__":
    total = embed_task()
    print(f"\nDONE — {total} offres embeddees au total.")