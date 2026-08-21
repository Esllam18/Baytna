#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up -d postgres
cd backend
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python ../scripts/seed_dev.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
