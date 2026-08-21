from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    'backend/app/main.py',
    'backend/app/core/config.py',
    'backend/alembic/versions/0017_sprint32_paymob_reconciliation.py',
    'backend/alembic/versions/0018_sprint43_operations_control_room.py',
    'backend/alembic/versions/0022_sprint47_financial_reconciliation_rollout.py',
    'backend/alembic/versions/0023_sprint48_launch_traffic_vendor_accounting.py',
    'backend/alembic/versions/0024_sprint49_launch_command_center.py',
    'backend/tests/test_customer_app_checkout_contract.py',
    'apps/customer_app/package.json',
    'apps/customer_app/app.json',
    'apps/customer_app/assets/baytna-logo.png',
    'apps/customer_app/app/cart.tsx',
    'apps/customer_app/app/checkout.tsx',
    'apps/customer_app/app/payment/result.tsx',
    'apps/customer_app/app/orders/index.tsx',
    'apps/customer_app/app/orders/[orderId].tsx',
    'apps/customer_app/app/orders/[orderId]/tracking.tsx',
    'apps/customer_app/src/hooks/useCommerce.ts',
    'apps/customer_app/src/payment/pendingPayment.ts',
    'apps/customer_app/src/ui/CartLineItem.tsx',
    'apps/customer_app/src/ui/PriceSummary.tsx',
    'apps/customer_app/src/ui/OrderStatusCard.tsx',
    'scripts/verify_customer_app_contract.py',
    'scripts/verify_frontend_static.py',
    'docs/SPRINT_35.md',
    'docs/CHECKOUT_PAYMENT_UI.md',
    'docs/LIVE_TRACKING_UI.md',
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit('Missing files: ' + ', '.join(missing))
print('Sprint 35 structure verified.')
