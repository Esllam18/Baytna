from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/app/modules/driver_app/router.py",
    "backend/app/modules/driver_app/service.py",
    "backend/app/modules/driver_app/schemas.py",
    "backend/tests/test_sprint39_driver_app_contract.py",
    "apps/driver_app/package.json",
    "apps/driver_app/app/auth/login.tsx",
    "apps/driver_app/app/auth/verify.tsx",
    "apps/driver_app/app/home.tsx",
    "apps/driver_app/app/missions/index.tsx",
    "apps/driver_app/app/missions/[missionId].tsx",
    "apps/driver_app/app/missions/[missionId]/proof.tsx",
    "apps/driver_app/app/history.tsx",
    "apps/driver_app/src/media/uploadDeliveryProof.ts",
    "apps/driver_app/src/navigation/maps.ts",
    "scripts/verify_driver_app_contract.py",
    "scripts/verify_driver_frontend_static.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Missing Sprint 39 files: "+", ".join(missing))
print("Sprint 39 structure verified.")
