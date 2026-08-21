from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0024_sprint49_launch_command_center.py",
    "backend/app/modules/launch_command/__init__.py",
    "backend/app/modules/launch_command/schemas.py",
    "backend/app/modules/launch_command/service.py",
    "backend/app/modules/launch_command/router.py",
    "backend/tests/test_sprint49_launch_command_center.py",
    "apps/admin_dashboard/src/pages/LaunchCommand.tsx",
    "scripts/pilot_launch_command_evidence.py",
    "scripts/verify_sprint49_contract.py",
    "scripts/verify_sprint49_static.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 49 structure missing: "+", ".join(missing))
print("Sprint 49 structure verified.")
