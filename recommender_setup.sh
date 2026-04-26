#!/bin/bash
# recommender_setup.sh — Setup script for Job Recommender System

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Job Recommender System — Setup Script                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 1. Check Python
echo "1️⃣  Checking Python..."
python --version || { echo "❌ Python not found"; exit 1; }

# 2. Install requirements
echo ""
echo "2️⃣  Installing dependencies..."
pip install -r requirements.txt || { echo "❌ pip install failed"; exit 1; }

# 3. Download spaCy models
echo ""
echo "3️⃣  Downloading spaCy language models..."
echo "   → French model (fr_core_news_md)..."
python -m spacy download fr_core_news_md 2>/dev/null || echo "   ⚠️  May require manual install"
echo "   → English model (en_core_web_md)..."
python -m spacy download en_core_web_md 2>/dev/null || echo "   ⚠️  May require manual install"

# 4. Check environment
echo ""
echo "4️⃣  Checking environment variables..."
if [ -z "$SUPABASE_API_URL" ] || [ -z "$SUPABASE_API_KEY" ]; then
    echo "   ⚠️  Environment variables not set in shell"
    echo "   ℹ️  Loading from .env file..."
    if [ -f ".env" ]; then
        source .env
        echo "   ✅ .env loaded (SUPABASE_API_URL, SUPABASE_API_KEY)"
    else
        echo "   ❌ .env file not found"
        exit 1
    fi
else
    echo "   ✅ Environment variables set"
fi

# 5. Test imports
echo ""
echo "5️⃣  Testing Python imports..."
python -c "
import fastapi, uvicorn, supabase, sentence_transformers, pdfplumber, docx, spacy, langdetect
print('   ✅ All imports successful')
" || { echo "   ❌ Import failed"; exit 1; }

# 6. Summary
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              ✅ Setup Complete!                          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Next steps:"
echo ""
echo "1. Start the FastAPI server:"
echo "   uvicorn scrapers.recommender:app --reload --port 8000"
echo ""
echo "2. Open the frontend:"
echo "   - Automatic API docs: http://localhost:8000/docs"
echo "   - Web UI: Open index.html in your browser"
echo ""
echo "3. Test with a sample CV:"
echo "   curl -X POST http://localhost:8000/recommend/cv -F 'file=@sample.pdf'"
echo ""
echo "📖 For more info, see: RECOMMENDER_README.md"
echo ""
