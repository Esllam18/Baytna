from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/alembic/versions/0025_sprint50_post_launch_stabilization.py",
    "backend/app/modules/post_launch/__init__.py",
    "backend/app/modules/post_launch/schemas.py",
    "backend/app/modules/post_launch/service.py",
    "backend/app/modules/post_launch/router.py",
    "backend/tests/test_sprint50_post_launch_stabilization.py",
    "apps/admin_dashboard/src/pages/PostLaunch.tsx",
    "scripts/pilot_post_launch_stabilization_evidence.py",
    "scripts/expansion_review_gate.py",
    "scripts/verify_sprint50_contract.py",
    "scripts/verify_sprint50_static.py",
]
missing = [path for path in required if not (ROOT / path).exists()]
if missing:
    raise SystemExit("Sprint 50 structure missing: " + ", ".join(missing))
print("Sprint 50 structure verified.")
