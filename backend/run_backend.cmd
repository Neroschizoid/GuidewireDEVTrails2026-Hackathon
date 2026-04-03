@echo off
REM Runs the FastAPI backend from the correct working directory.
cd /d "%~dp0"

REM Optional: set DATABASE_URL and CORS_ORIGINS here or via PowerShell.
REM set DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/gig_insurance

uvicorn app.main:app --reload --port 8000

