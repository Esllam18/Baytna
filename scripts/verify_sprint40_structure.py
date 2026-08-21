from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "backend/tests/test_sprint40_admin_dashboard_contract.py",
 "apps/admin_dashboard/src/pages/Dashboard.tsx",
 "apps/admin_dashboard/src/pages/Orders.tsx",
 "apps/admin_dashboard/src/pages/Chefs.tsx",
 "apps/admin_dashboard/src/pages/Drivers.tsx",
 "apps/admin_dashboard/src/pages/Support.tsx",
 "apps/admin_dashboard/src/pages/Finance.tsx",
 "scripts/verify_admin_dashboard_contract.py",
 "scripts/verify_admin_frontend_static.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit("Missing Sprint 40 files: "+", ".join(missing))
print("Sprint 40 structure verified.")
