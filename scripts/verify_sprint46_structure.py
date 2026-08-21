from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0021_sprint46_operational_economics.py",
    "backend/app/modules/operational_economics/__init__.py",
    "backend/app/modules/operational_economics/schemas.py",
    "backend/app/modules/operational_economics/service.py",
    "backend/app/modules/operational_economics/router.py",
    "backend/tests/test_sprint46_operational_economics.py",
    "apps/admin_dashboard/src/pages/Economics.tsx",
    "scripts/verify_sprint46_contract.py",
    "scripts/verify_sprint46_static.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 46 structure missing: "+", ".join(missing))
print("Sprint 46 structure verified.")
