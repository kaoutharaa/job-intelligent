"""
cv_parser.py
─────────────────────────────────────────────────────────────────
Extrait automatiquement les informations d'un CV (PDF ou DOCX) :
  - Titre / poste actuel
  - Compétences techniques
  - Années d'expérience
  - Formation
  - Langues

Supporte : Français, Anglais, Arabe (détection automatique)

Dépendances (requirements.txt) :
    pdfplumber>=0.10.0
    python-docx>=1.1.0
    spacy>=3.7.0
    langdetect>=1.0.9
"""

import re
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

import pdfplumber
import docx
import spacy
from langdetect import detect

log = logging.getLogger(__name__)

# ── Chargement des modèles spaCy ────────────────────────────
_nlp_fr = None
_nlp_en = None

def _get_nlp(lang: str):
    global _nlp_fr, _nlp_en
    if lang == "fr":
        if _nlp_fr is None:
            try:
                _nlp_fr = spacy.load("fr_core_news_md")
            except:
                log.warning("French spaCy model not found. Install with: python -m spacy download fr_core_news_md")
                _nlp_fr = None
        return _nlp_fr
    else:
        if _nlp_en is None:
            try:
                _nlp_en = spacy.load("en_core_web_md")
            except:
                log.warning("English spaCy model not found. Install with: python -m spacy download en_core_web_md")
                _nlp_en = None
        return _nlp_en


TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "r", "scala", "c++", "c#",
    "go", "rust", "php", "ruby", "swift", "kotlin", "matlab",
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "keras",
    "pytorch", "transformers", "spacy", "nltk", "xgboost", "lightgbm",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "spark", "pyspark", "hadoop", "kafka", "airflow", "dbt",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "fastapi", "flask", "django", "react", "node.js",
    "excel", "power bi", "tableau", "looker", "metabase",
}

LANGUAGES_KEYWORDS = {
    "français": "Français", "french": "Français",
    "anglais": "Anglais", "english": "Anglais",
    "arabe": "Arabe", "arabic": "Arabe",
    "espagnol": "Espagnol", "spanish": "Espagnol",
}

JOB_TITLES = [
    "data scientist", "data engineer", "data analyst", "machine learning engineer",
    "mlops engineer", "ai engineer", "nlp engineer", "business intelligence",
    "software engineer", "backend developer", "frontend developer",
    "product manager", "project manager", "cloud engineer", "devops engineer",
]


@dataclass
class ParsedCV:
    raw_text         : str           = ""
    detected_lang    : str           = "fr"
    full_name        : Optional[str] = None
    current_title    : Optional[str] = None
    years_experience : int           = 0
    skills           : list[str]     = field(default_factory=list)
    languages        : list[str]     = field(default_factory=list)
    education        : list[str]     = field(default_factory=list)
    profile_summary  : str           = ""

    def to_profile_dict(self) -> dict:
        return {
            "current_title"    : self.current_title,
            "years_experience" : self.years_experience,
            "skills"           : self.skills,
            "languages"        : self.languages,
            "profile_summary"  : self.profile_summary,
        }


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte d'un PDF."""
    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        log.error(f"PDF extraction error: {e}")
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrait le texte d'un DOCX."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        log.error(f"DOCX extraction error: {e}")
        return ""


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Détecte le format et extrait le texte."""
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif fname.endswith(".docx") or fname.endswith(".doc"):
        return extract_text_from_docx(file_bytes)
    return ""


def detect_language(text: str) -> str:
    try:
        lang = detect(text[:500])
        return "fr" if lang in ("fr", "ar") else "en"
    except:
        return "fr"


def extract_name(text: str, nlp) -> Optional[str]:
    """Extrait le nom depuis la première ligne."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        first = lines[0]
        if len(first.split()) <= 4 and not any(c.isdigit() for c in first):
            return first.title()
    
    if nlp:
        try:
            doc = nlp(text[:500])
            for ent in doc.ents:
                if ent.label_ == "PER":
                    return ent.text.title()
        except:
            pass
    return None


def extract_title(text: str) -> Optional[str]:
    """Cherche un titre de poste."""
    lines = [l.strip().lower() for l in text.split("\n")[:15] if l.strip()]
    for line in lines:
        for title in JOB_TITLES:
            if title in line:
                return title.title()
    return None


def extract_skills(text: str) -> list[str]:
    """Détecte les compétences techniques."""
    text_lower = text.lower()
    found = set()
    for skill in TECH_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill.title() if len(skill) > 2 else skill.upper())
    return sorted(found)


def extract_languages(text: str) -> list[str]:
    """Détecte les langues."""
    text_lower = text.lower()
    found = set()
    for keyword, label in LANGUAGES_KEYWORDS.items():
        if keyword in text_lower:
            found.add(label)
    return sorted(found)


def extract_years_experience(text: str) -> int:
    """Estime les années d'expérience."""
    patterns = [
        r'(\d+)\s*(?:ans?|années?)\s*(?:d[\'e]?\s*)?expérience',
        r'(\d+)\s*years?\s*(?:of\s*)?experience',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            years = int(match.group(1))
            if 0 < years < 50:
                return years
    return 0


def extract_education(text: str, lang: str) -> list[str]:
    """Extrait les formations."""
    diplomas = []
    diploma_patterns = [
        r'\b(master|licence|bachelor|engineering|phd|mba|bts|dut)\b',
    ]
    lines = text.lower().split("\n")
    for line in lines:
        for pattern in diploma_patterns:
            if re.search(pattern, line):
                diplomas.append(line.strip().title()[:120])
                break
    return diplomas[:5]


def build_profile_summary(parsed: "ParsedCV") -> str:
    """Construit un texte condensé pour embedding."""
    parts = []
    if parsed.current_title:
        parts.append(parsed.current_title)
    if parsed.years_experience:
        parts.append(f"{parsed.years_experience} ans d'expérience")
    if parsed.skills:
        parts.append("Compétences : " + ", ".join(parsed.skills[:15]))
    if parsed.languages:
        parts.append("Langues : " + ", ".join(parsed.languages))
    if parsed.education:
        parts.append("Formation : " + " | ".join(parsed.education[:2]))
    return " | ".join(parts)


def parse_cv(file_bytes: bytes, filename: str) -> ParsedCV:
    """Parse complet d'un CV."""
    log.info(f"Parsing CV: {filename} ({len(file_bytes)} bytes)")

    raw_text = extract_text(file_bytes, filename)
    if not raw_text.strip():
        log.warning(f"CV empty: {filename}")
        return ParsedCV(raw_text="")

    lang = detect_language(raw_text)
    nlp = _get_nlp(lang)

    parsed = ParsedCV(
        raw_text         = raw_text,
        detected_lang    = lang,
        full_name        = extract_name(raw_text, nlp),
        current_title    = extract_title(raw_text),
        years_experience = extract_years_experience(raw_text),
        skills           = extract_skills(raw_text),
        languages        = extract_languages(raw_text),
        education        = extract_education(raw_text, lang),
    )

    parsed.profile_summary = build_profile_summary(parsed)

    log.info(
        f"✅ CV parsed — title: {parsed.current_title} | "
        f"skills: {len(parsed.skills)} | experience: {parsed.years_experience} years"
    )
    return parsed
