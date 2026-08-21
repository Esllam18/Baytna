from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0022_sprint47_financial_reconciliation_rollout.py",
    "backend/app/modules/financial_automation/__init__.py",
    "backend/app/modules/financial_automation/schemas.py",
    "backend/app/modules/financial_automation/service.py",
    "backend/app/modules/financial_automation/router.py",
    "backend/tests/test_sprint47_financial_automation.py",
    "apps/admin_dashboard/src/pages/FinancialAutomation.tsx",
    "scripts/pilot_financial_automation_evidence.py",
    "scripts/verify_sprint47_contract.py",
    "scripts/verify_sprint47_static.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 47 structure missing: "+", ".join(missing))
print("Sprint 47 structure verified.")
