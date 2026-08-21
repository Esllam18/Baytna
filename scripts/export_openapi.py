import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# OpenAPI generation should not require a running PostgreSQL instance.
os.environ.setdefault("BAYTNA_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("BAYTNA_SEED_DEMO_DATA", "false")
os.environ.setdefault(
    "BAYTNA_JWT_SECRET",
    "openapi-generation-secret-32-characters-minimum",
)

from app.main import app

target = ROOT / "contracts" / "openapi.json"
target.write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(target)
