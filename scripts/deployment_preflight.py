from __future__ import annotations

import sys

from sqlalchemy import text

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.core.database import build_engine


def main() -> int:
    try:
        settings = Settings()
    except Exception as exc:
        print(f"PRECHECK FAILED: {exc}")
        return 2

    print(f"Environment: {settings.env}")
    print(f"Database target: {settings.database_url.split('://', 1)[0]}")
    print(f"Allowed hosts: {', '.join(settings.allowed_host_list)}")
    print(f"CORS origins: {', '.join(settings.cors_origin_list)}")

    try:
        engine = build_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"DATABASE CHECK FAILED: {exc}")
        return 3

    print("Deployment preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
