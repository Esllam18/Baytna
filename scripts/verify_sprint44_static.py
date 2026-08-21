from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    "backend/app/modules/delivery_timing/service.py",
    "backend/alembic/versions/0019_sprint44_delivery_timing.py",
    "backend/tests/test_sprint44_delivery_timing.py",
    "scripts/pilot_delivery_timing_evidence.py",
    "apps/customer_app/app/orders/[orderId]/tracking.tsx",
    "apps/driver_app/app/missions/[missionId].tsx",
    "apps/admin_dashboard/src/pages/ControlRoom.tsx",
    "apps/admin_dashboard/src/pages/OrderDetail.tsx",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit(
        "Missing Sprint 44 files: " + ", ".join(missing)
    )

timing = (
    ROOT / "backend/app/modules/delivery_timing/service.py"
).read_text(encoding="utf-8")
delivery = (
    ROOT / "backend/app/modules/delivery/service.py"
).read_text(encoding="utf-8")
ops = (
    ROOT / "backend/app/modules/operations_control/service.py"
).read_text(encoding="utf-8")
control = (
    ROOT / "apps/admin_dashboard/src/pages/ControlRoom.tsx"
).read_text(encoding="utf-8")
customer = (
    ROOT / "apps/customer_app/app/orders/[orderId]/tracking.tsx"
).read_text(encoding="utf-8")
driver = (
    ROOT / "apps/driver_app/app/missions/[missionId].tsx"
).read_text(encoding="utf-8")
gate = (
    ROOT / "scripts/go_live_gate.py"
).read_text(encoding="utf-8")
pilot_env = (ROOT / ".env.pilot.example").read_text(encoding="utf-8")

for symbol in [
    "promised_delivery_window_start_at",
    "promised_delivery_window_end_at",
    "delivery_promise_snapshot_at",
    "delivery_timing_status",
    "late_by_minutes",
]:
    assert symbol in timing or symbol in delivery

assert 'fingerprint=f"delivery_promise:{order.id}"' in ops
assert "ops_incident_auto_escalate_minutes" in ops
assert "_notify_admins" in ops
assert 'kind="ops_incident"' in ops
assert "delivery_promise_coverage_pct" in ops
assert "on_time_delivery_rate_pct" in ops
assert "promised delivery window" in (
    ROOT / "scripts/pilot_delivery_timing_evidence.py"
).read_text(encoding="utf-8")

assert "موعد التوصيل المتفق عليه" in customer
assert "موعد التسليم المستهدف" in driver
assert "Promise coverage" in control
assert "Late deliveries" in control
assert "delivery_promise_live_order_verified" in gate
assert "ops_incident_notification_verified" in gate
assert "BAYTNA_DELIVERY_PROMISE_REQUIRED=true" in pilot_env
assert "BAYTNA_DELIVERY_PROMISE_TIMEZONE=Africa/Cairo" in pilot_env

health = (
    ROOT / "backend/app/modules/health/router.py"
).read_text(encoding="utf-8")
assert '"0021_sprint46"' in health

print("Inherited Sprint 44 timing/escalation/static verification passed under Sprint 45.")
