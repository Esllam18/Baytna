from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.seed import seed_demo_data


if not get_settings().seed_demo_data:
    print("Demo seed disabled.")
    raise SystemExit(0)

with SessionLocal() as db:
    seed_demo_data(db)

print("Baytna demo chefs seeded.")
