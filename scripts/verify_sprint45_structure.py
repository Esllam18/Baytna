from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/alembic/versions/0020_sprint45_pilot_stability.py",
    "backend/app/modules/pilot_stability/__init__.py",
    "backend/app/modules/pilot_stability/schemas.py",
    "backend/app/modules/pilot_stability/service.py",
    "backend/app/modules/pilot_stability/router.py",
    "apps/admin_dashboard/src/pages/Pilot.tsx",
    "scripts/verify_sprint45_contract.py",
    "scripts/verify_sprint45_static.py",
    "scripts/pilot_scale_evidence.py",
    "scripts/pilot_scale_gate.py",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit("Sprint 45 structure missing: " + ", ".join(missing))
print("Sprint 45 structure verified.")
