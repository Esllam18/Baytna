@echo off
setlocal
cd /d "%~dp0"

if not exist .env copy .env.example .env >nul

docker compose up -d postgres
if errorlevel 1 exit /b 1

cd backend
python -m pip install -e .[dev]
if errorlevel 1 exit /b 1

python -m alembic upgrade head
if errorlevel 1 exit /b 1

python ..\scripts\seed_dev.py
if errorlevel 1 exit /b 1

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
