from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/alembic/versions/0019_sprint44_delivery_timing.py",
    "backend/app/modules/delivery_timing/__init__.py",
    "backend/app/modules/delivery_timing/service.py",
    "backend/tests/test_sprint44_delivery_timing.py",
    "scripts/verify_sprint44_contract.py",
    "scripts/verify_sprint44_static.py",
    "scripts/pilot_delivery_timing_evidence.py",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit(
        "Sprint 44 structure missing: " + ", ".join(missing)
    )
print("Sprint 44 structure verified.")
