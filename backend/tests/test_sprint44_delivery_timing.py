from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.db_models import (
    ChefWorkdayEntity,
    DeliveryTaskEntity,
    NotificationDeliveryEntity,
    NotificationEntity,
    OperationsIncidentEntity,
    OrderEntity,
    SupportTicketEntity,
)
from app.core.errors import ApiError
from app.core.security import utc_now
from app.modules.delivery_timing.service import DeliveryTimingService
from tests.test_admin_operations import (
    CHEF_ID,
    admin_headers,
    make_order,
)
from tests.test_delivery import (
    DRIVER_1_PHONE,
    create_ready_order,
    make_driver_available,
)
from tests.test_orders import (
    CHEF_1_ID,
    CHEF_1_PHONE,
    login_phone,
)


def _future_date(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _publish_with_window(
    client,
    *,
    service_date: str,
    window_start: str = "13:00",
    window_end: str = "15:00",
):
    chef = login_phone(client, CHEF_1_PHONE)

    opened = client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "delivery_window_start": window_start,
            "delivery_window_end": window_end,
        },
    )
    assert opened.status_code == 200

    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    )
    assert signature.status_code == 200
    dish_id = signature.json()[0]["id"]

    published = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {
                    "dish_id": dish_id,
                    "quantity_total": 10,
                    "max_per_order": 5,
                }
            ],
        },
    )
    assert published.status_code == 200
    return published.json()["items"][0]


def _create_pending_with_window(login, *, service_date: str):
    client = login["client"]
    menu_item = _publish_with_window(
        client,
        service_date=service_date,
    )
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 1,
        },
    )
    assert cart.status_code == 201

    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart.json()["id"]},
    )
    assert order.status_code == 201
    return order.json()


def test_standard_order_snapshots_delivery_window_in_cairo_timezone(login):
    service_date = _future_date(70)
    order = _create_pending_with_window(
        login,
        service_date=service_date,
    )

    assert order["promised_delivery_timezone"] == "Africa/Cairo"
    assert order["delivery_promise_source"] == "today_kitchen"
    assert order["promised_delivery_window_start_at"]
    assert order["promised_delivery_window_end_at"]

    zone = ZoneInfo("Africa/Cairo")
    expected_start = datetime.combine(
        date.fromisoformat(service_date),
        time(13, 0),
        tzinfo=zone,
    ).astimezone(timezone.utc)
    expected_end = datetime.combine(
        date.fromisoformat(service_date),
        time(15, 0),
        tzinfo=zone,
    ).astimezone(timezone.utc)

    actual_start = datetime.fromisoformat(
        order["promised_delivery_window_start_at"]
    )
    actual_end = datetime.fromisoformat(
        order["promised_delivery_window_end_at"]
    )
    assert actual_start == expected_start
    assert actual_end == expected_end

    # Snapshot must stay on the order even if the workday changes later.
    with SessionLocal() as db:
        workday = db.scalar(
            select(ChefWorkdayEntity).where(
                ChefWorkdayEntity.chef_id == UUID(CHEF_1_ID),
                ChefWorkdayEntity.service_date
                == date.fromisoformat(service_date),
            )
        )
        workday.delivery_window_start = "16:00"
        workday.delivery_window_end = "18:00"
        db.commit()

    detail = login["client"].get(
        f"/api/v1/customer/orders/{order['id']}",
        headers=login["headers"],
    )
    assert detail.status_code == 200
    assert (
        detail.json()["promised_delivery_window_end_at"]
        == order["promised_delivery_window_end_at"]
    )


def test_required_delivery_promise_fails_closed_without_window():
    timing = DeliveryTimingService(
        Settings(delivery_promise_required=True)
    )
    with pytest.raises(ApiError) as exc:
        timing.snapshot(
            service_date=date.today(),
            window_start=None,
            window_end=None,
            source="test",
        )
    assert exc.value.code == "delivery_window_required"


def test_delivery_completion_stamps_late_outcome_and_tracking(login):
    client = login["client"]
    _, order = create_ready_order(
        client,
        login,
        _future_date(71),
    )
    order_id = UUID(order["id"])

    with SessionLocal() as db:
        row = db.get(OrderEntity, order_id)
        row.promised_delivery_window_start_at = (
            utc_now() - timedelta(hours=1)
        )
        row.promised_delivery_window_end_at = (
            utc_now() - timedelta(minutes=8)
        )
        row.promised_delivery_timezone = "Africa/Cairo"
        row.delivery_promise_source = "test_fixture"
        row.delivery_promise_snapshot_at = utc_now() - timedelta(hours=2)
        db.commit()

    driver = make_driver_available(client, DRIVER_1_PHONE)
    missions = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    )
    mission = next(
        x for x in missions.json()
        if x["order_id"] == order["id"]
    )

    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/accept",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/arrive-pickup",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/confirm-pickup",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/start-delivery",
        headers=driver["headers"],
    ).status_code == 200

    delivered = client.post(
        f"/api/v1/driver/missions/{mission['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "manual",
            "proof_reference": "sprint44-late-proof",
        },
    )
    assert delivered.status_code == 200
    assert delivered.json()["delivery_timing_status"] == "late"
    assert delivered.json()["late_by_minutes"] >= 8
    assert delivered.json()["promised_delivery_window_end_at"]

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert tracking.status_code == 200
    assert tracking.json()["delivery_timing_status"] == "late"
    assert tracking.json()["late_by_minutes"] >= 8

    admin, _ = admin_headers()
    detail = client.get(
        f"/api/v1/admin/orders/{order['id']}",
        headers=admin,
    )
    assert detail.status_code == 200
    assert detail.json()["delivery"]["delivery_timing_status"] == "late"


def test_true_on_time_kpi_uses_promised_deadline_and_requires_full_coverage(client):
    first_id, _ = make_order(client, "delivered", 30000)
    second_id, _ = make_order(client, "delivered", 25000)
    now = utc_now()

    with SessionLocal() as db:
        first = db.get(OrderEntity, first_id)
        second = db.get(OrderEntity, second_id)

        first.promised_delivery_window_start_at = now - timedelta(hours=1)
        first.promised_delivery_window_end_at = now + timedelta(minutes=10)
        first.promised_delivery_timezone = "Africa/Cairo"
        first.delivery_promise_source = "test"

        second.promised_delivery_window_start_at = now - timedelta(hours=1)
        second.promised_delivery_window_end_at = now - timedelta(minutes=10)
        second.promised_delivery_timezone = "Africa/Cairo"
        second.delivery_promise_source = "test"

        db.add(
            DeliveryTaskEntity(
                order_id=first.id,
                chef_id=CHEF_ID,
                status="delivered",
                delivered_at=now,
                delivery_timing_status="on_time",
                late_by_minutes=0,
            )
        )
        db.add(
            DeliveryTaskEntity(
                order_id=second.id,
                chef_id=CHEF_ID,
                status="delivered",
                delivered_at=now,
                delivery_timing_status="late",
                late_by_minutes=10,
            )
        )
        db.commit()

    admin, _ = admin_headers()
    response = client.get(
        "/api/v1/admin/control-room/kpis",
        params={"days": 7},
        headers=admin,
    )
    assert response.status_code == 200
    kpis = response.json()

    assert kpis["on_time_measurable_deliveries"] == 2
    assert kpis["late_deliveries"] == 1
    assert kpis["delivery_promise_coverage_pct"] == 100.0
    assert kpis["on_time_delivery_rate_pct"] == 50.0
    assert kpis["launch_target_on_time_met"] is False

    third_id, _ = make_order(client, "delivered", 20000)
    with SessionLocal() as db:
        db.add(
            DeliveryTaskEntity(
                order_id=third_id,
                chef_id=CHEF_ID,
                status="delivered",
                delivered_at=utc_now(),
                delivery_timing_status="unmeasurable",
            )
        )
        db.commit()

    response = client.get(
        "/api/v1/admin/control-room/kpis",
        params={"days": 7},
        headers=admin,
    )
    kpis = response.json()
    assert kpis["delivery_promise_coverage_pct"] < 100.0
    assert kpis["launch_target_on_time_met"] is None


def test_delivery_promise_warning_becomes_critical_after_deadline(client):
    order_id, _ = make_order(
        client,
        status="out_for_delivery",
        total=28000,
    )
    with SessionLocal() as db:
        order = db.get(OrderEntity, order_id)
        order.promised_delivery_window_start_at = utc_now() - timedelta(hours=1)
        order.promised_delivery_window_end_at = utc_now() + timedelta(minutes=10)
        order.promised_delivery_timezone = "Africa/Cairo"
        order.delivery_promise_source = "test"
        db.commit()

    admin, _ = admin_headers()
    refreshed = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=admin,
    )
    assert refreshed.status_code == 200

    incidents = client.get(
        "/api/v1/admin/control-room/incidents",
        params={"category": "delivery_sla"},
        headers=admin,
    ).json()
    incident = next(
        x
        for x in incidents
        if x["fingerprint"] == f"delivery_promise:{order_id}"
    )
    assert incident["severity"] == "high"
    assert incident["details_json"]["remaining_minutes"] <= 10

    with SessionLocal() as db:
        order = db.get(OrderEntity, order_id)
        order.promised_delivery_window_end_at = (
            utc_now() - timedelta(minutes=4)
        )
        db.commit()

    client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=admin,
    )
    incidents = client.get(
        "/api/v1/admin/control-room/incidents",
        params={"category": "delivery_sla"},
        headers=admin,
    ).json()
    incident = next(
        x
        for x in incidents
        if x["fingerprint"] == f"delivery_promise:{order_id}"
    )
    assert incident["severity"] == "critical"
    assert incident["details_json"]["overdue_minutes"] >= 4


def test_unacknowledged_incident_auto_escalates_and_plans_admin_push(login):
    client = login["client"]
    admin_headers_value, admin_id = admin_headers()

    registered = client.post(
        "/api/v1/notifications/devices",
        headers=admin_headers_value,
        json={
            "platform": "android",
            "token": "sprint44-admin-fcm-token-000000000001",
            "device_name": "ops-pilot-admin",
            "app_version": "0.44.0",
        },
    )
    assert registered.status_code == 201

    customer_id = UUID(login["body"]["user"]["id"])
    with SessionLocal() as db:
        ticket = SupportTicketEntity(
            customer_id=customer_id,
            category="other",
            subject="Normal support SLA escalation",
            description="Sprint 44 automatic incident escalation.",
            priority="normal",
            status="new",
            created_at=utc_now() - timedelta(hours=5),
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id

    first = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=admin_headers_value,
    )
    assert first.status_code == 200

    with SessionLocal() as db:
        incident = db.scalar(
            select(OperationsIncidentEntity).where(
                OperationsIncidentEntity.fingerprint
                == f"support_sla:{ticket_id}"
            )
        )
        assert incident.severity == "warning"
        incident.detected_at = utc_now() - timedelta(minutes=20)
        db.commit()

    second = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=admin_headers_value,
    )
    assert second.status_code == 200
    assert second.json()["auto_escalated"] >= 1
    assert second.json()["admin_notifications_planned"] >= 1

    with SessionLocal() as db:
        incident = db.scalar(
            select(OperationsIncidentEntity).where(
                OperationsIncidentEntity.fingerprint
                == f"support_sla:{ticket_id}"
            )
        )
        assert incident.severity == "high"
        auto = incident.details_json["auto_escalation"]
        assert auto["count"] >= 1

        notification = db.scalar(
            select(NotificationEntity)
            .where(
                NotificationEntity.user_id == admin_id,
                NotificationEntity.kind == "ops_incident",
            )
            .order_by(NotificationEntity.created_at.desc())
        )
        assert notification is not None
        assert notification.data_json["incident_id"] == str(incident.id)

        delivery = db.scalar(
            select(NotificationDeliveryEntity).where(
                NotificationDeliveryEntity.notification_id == notification.id,
                NotificationDeliveryEntity.channel == "push",
            )
        )
        assert delivery is not None
        assert delivery.status == "pending"
