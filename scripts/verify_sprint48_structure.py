from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0023_sprint48_launch_traffic_vendor_accounting.py",
    "backend/app/modules/launch_governance/__init__.py",
    "backend/app/modules/launch_governance/schemas.py",
    "backend/app/modules/launch_governance/service.py",
    "backend/app/modules/launch_governance/router.py",
    "backend/app/modules/vendor_accounting/__init__.py",
    "backend/app/modules/vendor_accounting/schemas.py",
    "backend/app/modules/vendor_accounting/service.py",
    "backend/app/modules/vendor_accounting/router.py",
    "backend/tests/test_sprint48_launch_traffic_vendor_accounting.py",
    "apps/admin_dashboard/src/pages/TrafficGovernance.tsx",
    "apps/admin_dashboard/src/pages/VendorAccounting.tsx",
    "scripts/pilot_launch_governance_evidence.py",
    "scripts/verify_sprint48_contract.py",
    "scripts/verify_sprint48_static.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 48 structure missing: "+", ".join(missing))
print("Sprint 48 structure verified.")
