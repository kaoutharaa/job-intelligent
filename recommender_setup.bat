@echo off
REM recommender_setup.bat — Setup script for Job Recommender System (Windows)

cls
echo.
echo =====================================================
echo   Job Recommender System - Setup Script (Windows)
echo =====================================================
echo.

REM 1. Check Python
echo 1^) Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Python not found. Install from python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo    %%i

REM 2. Install requirements
echo.
echo 2^) Installing dependencies...
echo    This may take a few minutes...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERR] pip install failed
    pause
    exit /b 1
)
echo    [OK] Dependencies installed

REM 3. Download spaCy models
echo.
echo 3^) Downloading spaCy language models...
echo    This may take a few minutes...
echo    ^> French model (fr_core_news_md)...
python -m spacy download fr_core_news_md -q 2>nul
if errorlevel 1 echo    [WARN] French model failed (may need manual install)
if errorlevel 0 echo    [OK] French model downloaded

echo    ^> English model (en_core_web_md)...
python -m spacy download en_core_web_md -q 2>nul
if errorlevel 1 echo    [WARN] English model failed (may need manual install)
if errorlevel 0 echo    [OK] English model downloaded

REM 4. Check .env file
echo.
echo 4^) Checking environment configuration...
if not exist ".env" (
    echo    [ERR] .env file not found
    echo    [INFO] Create .env with:
    echo.
    echo    SUPABASE_API_URL=https://your-instance.supabase.co
    echo    SUPABASE_API_KEY=your_api_key
    echo.
    pause
    exit /b 1
)
echo    [OK] .env file found

REM 5. Test imports
echo.
echo 5^) Testing Python imports...
python -c "import fastapi, uvicorn, supabase, sentence_transformers, pdfplumber, docx, spacy, langdetect; print('[OK] All imports successful')" 2>nul
if errorlevel 1 (
    echo    [ERR] Import test failed
    pause
    exit /b 1
)

REM 6. Summary
echo.
echo =====================================================
echo   [DONE] Setup Complete!
echo =====================================================
echo.
echo NEXT STEPS:
echo.
echo 1. Start the API server:
echo    ^> Open PowerShell/CMD and run:
echo    ^> uvicorn scrapers.recommender:app --reload --port 8000
echo.
echo 2. Access the system:
echo    ^> API docs: http://localhost:8000/docs
echo    ^> Web UI: Open index.html in your browser
echo.
echo 3. Test with a sample CV:
echo    ^> curl -X POST http://localhost:8000/recommend/cv ^
echo      -F "file=@sample.pdf"
echo.
echo For detailed info, see: RECOMMENDER_README.md
echo.
pause
