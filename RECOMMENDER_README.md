# Système de Recommandation de Candidats

## 🎯 Vue d'ensemble

Le système de recommandation matching les candidats avec les meilleures offres d'emploi basé sur:
1. **Analyse sémantique du CV** - Extraction automatique des compétences, expérience, langues
2. **Embedding intelligent** - Conversion du profil candidat en vecteur numérique via sentence-transformers
3. **Recherche hybride** - Combination de recherche sémantique (pgvector) + matching par mots-clés (BM25)
4. **Ranking intelligent** - Score de pertinence combinant sémantique et mots-clés

---

## 📦 Architecture

```
scrapers/
├── cv_parser.py           # Extraction des infos du CV (titre, skills, expérience)
├── embed_pipeline.py      # Génération des embeddings pour jobs & candidats
├── recommender.py         # API FastAPI - Endpoint de recommandation
└── ... (autres modules)

sql/
├── medallion_schema.sql   # Tables silver_jobs avec colonne embedding
├── recommender_schema.sql # Tables candidate_profiles & recommendation_logs
└── gold_analytics_queries.sql

index.html                 # Frontend web pour upload CV
```

---

## 🚀 Installation et lancement

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

Les packages clés:
- **fastapi** - Framework API web
- **uvicorn** - Serveur ASGI
- **sentence-transformers** - Modèle d'embeddings multilingue
- **supabase** - Client pour la base de données cloud
- **pdfplumber, python-docx** - Parseur de CV
- **spacy, langdetect** - NLP pour extraction d'infos

### 2. Télécharger les modèles spaCy

```bash
python -m spacy download fr_core_news_md
python -m spacy download en_core_web_md
```

### 3. Configurer l'environnement

Vérifier le fichier `.env`:
```env
SUPABASE_API_URL=https://votre-instance.supabase.co
SUPABASE_API_KEY=votre_api_key
```

### 4. Préparer la base de données

Exécuter les scripts SQL:
1. `sql/medallion_schema.sql` - Ajoute colonne `embedding` à `silver_jobs`
2. `sql/recommender_schema.sql` - Crée les tables de recommandation

```sql
-- Exemple: fonction pgvector pour recherche sémantique
CREATE FUNCTION match_jobs(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.2,
    match_count INT DEFAULT 50
)
RETURNS TABLE(job_id TEXT, title TEXT, similarity FLOAT, ...)
```

### 5. Générer les embeddings des offres

Pour utiliser le système, les offres d'emploi doivent avoir des embeddings. Deux options:

**Option A: Tâche Airflow (intégration pipeline)**
```python
# Dans dags/medallion_pipeline_dag.py
from scrapers.embed_pipeline import embed_task

embed_jobs = PythonOperator(
    task_id="embed_jobs",
    python_callable=embed_task,
    execution_timeout=timedelta(hours=3),
)
```

**Option B: Lancer manuellement**
```bash
python -c "from scrapers.embed_pipeline import EmbedPipeline; p = EmbedPipeline(); print(p.embed_jobs_batch())"
```

### 6. Démarrer l'API FastAPI

```bash
uvicorn scrapers.recommender:app --reload --host 0.0.0.0 --port 8000
```

Accès:
- API: http://localhost:8000
- Documentation interactive: http://localhost:8000/docs
- Frontend: file:///path/to/index.html

---

## 📡 API Endpoints

### 1. Upload CV et obtenir recommandations

```bash
curl -X POST http://localhost:8000/recommend/cv \
  -F "file=@mon_cv.pdf" \
  -F "top_k=10" \
  -F "alpha=0.7"
```

**Réponse:**
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
      "job_id": "job_123",
      "title": "Senior Data Engineer",
      "company": "TechCorp",
      "location": "Paris",
      "contract": "CDI",
      "skills": ["Python", "Spark", "AWS"],
      "url": "https://...",
      "score": 0.89
    },
    ...
  ],
  "generated_at": "2026-04-19T10:30:00Z"
}
```

**Paramètres:**
- `file` (required) - Fichier PDF ou DOCX
- `top_k` (optional, default=10) - Nombre de résultats (1-50)
- `alpha` (optional, default=0.7) - Poids sémantique vs mots-clés (0-1)
  - alpha=1.0 → priorité sémantique
  - alpha=0.0 → priorité mots-clés

### 2. Profil JSON (sans CV)

```bash
curl -X POST http://localhost:8000/recommend/profile \
  -H "Content-Type: application/json" \
  -d '{
    "current_title": "Data Analyst",
    "skills": ["Python", "Excel", "Tableau"],
    "years_experience": 3,
    "desired_titles": ["Data Engineer", "Analytics Engineer"],
    "desired_locations": ["Paris", "Lyon"]
  }'
```

### 3. Santé de l'API

```bash
curl http://localhost:8000/health
```

---

## 🔧 Comment ça marche

### Flux d'un CV

```
1. Upload CV
    ↓
2. Parsing CV (cv_parser.py)
    - Extraction: titre, compétences, expérience, langues
    - Détection: langue (FR/EN), années d'expérience
    ↓
3. Construction profile_summary
    "Data Engineer | 5 ans d'expérience | Compétences: Python, SQL, Spark..."
    ↓
4. Encoding par SentenceTransformer
    → Vecteur 768-dimensions (embedding)
    ↓
5. Requête Supabase - pgvector
    - Recherche sémantique: jobs similaires (cosine similarity > 0.2)
    - Retour: ~50 candidats (SEMANTIC_CANDIDATES)
    ↓
6. Scoring hybride
    - BM25: score keyword-based sur titre + skills
    - Normalize: [0, 1] pour sémantique et BM25
    - RRF (Reciprocal Rank Fusion): fusion intelligente
    ↓
7. Top-K et retour
    - Sort par final_score
    - Return top 10 (ou valeur top_k)
```

### Algorithmes

**BM25 (Keyword Matching)**
```python
score(query, doc) = Σ_term ( IDF(term) × (TF × (k1 + 1)) / (TF + k1(1 - b + b×(doc_len/avg_len))) )
```

**RRF (Reciprocal Rank Fusion)**
```python
score = α × (1/(k + sem_rank)) + (1-α) × (1/(k + bm25_rank))
```
- Combine ranking semantic + keyword
- k=60 (standard)
- α contrôle le poids

---

## 📊 Database Schema

### silver_jobs (Medallion - Silver Layer)

```sql
CREATE TABLE silver_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT UNIQUE,
    title TEXT,
    company TEXT,
    location_normalized TEXT,
    contract_type TEXT,
    keywords TEXT[],
    embedding VECTOR(768),       -- ← Nouvel!
    embedded_at TIMESTAMP,       -- ← Nouvel!
    ...
);

CREATE INDEX idx_silver_embedding 
ON silver_jobs USING ivfflat (embedding vector_cosine_ops);
```

### candidate_profiles

```sql
CREATE TABLE candidate_profiles (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT,
    current_title TEXT,
    years_experience INTEGER,
    skills TEXT[],
    languages TEXT[],
    profile_summary TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMP,
    ...
);
```

### recommendation_logs

```sql
CREATE TABLE recommendation_logs (
    id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT,
    job_id TEXT,
    semantic_score FLOAT,
    keyword_score FLOAT,
    final_score FLOAT,
    recommended_at TIMESTAMP
);
```

---

## 🎨 Frontend Web

Fichier: `index.html`

**Fonctionnalités:**
- Upload CV par drag-and-drop
- Affichage du profil extrait
- Listing des offres avec scores
- Lien vers offres originales
- Contrôles: top_k, alpha

**Lancement:**
```bash
# Option 1: Ouvrir directement
file:///chemin/to/index.html

# Option 2: Serveur local
python -m http.server 8080
# Puis: http://localhost:8080
```

---

## 🔍 Testing

### 1. Health Check

```bash
curl http://localhost:8000/health
# → {"status":"ok","timestamp":"2026-04-19T..."}
```

### 2. Test recommandation avec PDF

```bash
curl -X POST http://localhost:8000/recommend/cv \
  -F "file=@sample_cv.pdf" \
  -F "top_k=5" \
  | jq .
```

### 3. Swagger UI interactif

```
http://localhost:8000/docs
```

---

## ⚙️ Tuning et Performance

### Paramètres clés

| Paramètre | Défaut | Plage | Impact |
|-----------|--------|-------|---------|
| `ALPHA` | 0.7 | 0-1 | Poids sémantique vs keywords |
| `SEMANTIC_CANDIDATES` | 50 | 10-200 | Candidats pré-filtrés par sémantique |
| `BM25_K1` | 1.5 | 0.5-3 | Saturation terme-fréquence |
| `BM25_B` | 0.75 | 0-1 | Normalisation longueur doc |

### Optimisation

1. **Embeddings plus rapides**: Augmenter batch_size dans `embed_pipeline.py`
   ```python
   pipeline.embed_jobs_batch(batch_size=200)  # Défaut: 50
   ```

2. **Recherche sémantique**: Augmenter `match_threshold` → moins de résultats mais plus rapide
   ```python
   match_jobs(..., match_threshold=0.4)  # Défaut: 0.2
   ```

3. **Cache pgvector**: Optimizer les index IVFFlat
   ```sql
   SELECT pg_size_pretty(pg_total_relation_size('silver_jobs'));
   ```

---

## 🐛 Troubleshooting

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Service not available" | Supabase/model not loaded | Vérifier `.env`, redémarrer API |
| "Vector search failed" | pgvector pas activé | Exécuter `CREATE EXTENSION vector;` |
| "CV parsing failed" | Format non supporté | Utiliser PDF ou DOCX valide |
| "Module not found" | Dépendance manquante | `pip install -r requirements.txt` |
| "Slow embeddings" | GPU pas utilisé | CPU normal, acceptable |

---

## 📈 Métriques et Monitoring

Logs disponibles:
```
[INFO] Parsing CV: mon_cv.pdf (250 bytes)
[INFO] ✅ CV parsed — title: Data Engineer | skills: 8 | experience: 5 years
[INFO] Starting job embeddings...
[INFO] Processing 150 jobs...
[INFO] ✅ Embedding complete: 150 jobs
```

---

## 🚀 Prochaines étapes

1. **Intégrer au DAG Airflow** - Embedding automatique des nouvelles offres
2. **A/B Testing** - Tester différentes valeurs d'alpha
3. **User Feedback** - Log des clics "offres intéressantes"
4. **Recommandation améliorée** - Machine learning pour ajuster alpha par utilisateur
5. **Mobile App** - Version mobile du frontend

---

## 📝 Exemples de CV

Créer `test_cv.pdf` ou `test_cv.docx` avec:
```
JEAN DUPONT
Data Engineer

Expérience: 5 ans

Compétences:
- Python, SQL, PySpark
- AWS (EC2, S3, RDS)
- Airflow, dbt
- Git, Docker

Langues: Français, Anglais

Formation:
- Master Data Science
- Ecole d'ingénieurs
```

---

## 📞 Support

Pour toute question, consultez:
- API Docs: http://localhost:8000/docs
- Code source: `scrapers/recommender.py`
- Configuration: `.env`
