from datetime import date, timedelta
from uuid import UUID

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    ChefOrderFulfillmentEntity,
    OperationsIncidentEntity,
    SupportTicketEntity,
)
from app.core.security import utc_now
from app.modules.reliability.jobs import BackgroundJobService
from tests.test_admin_operations import admin_headers
from tests.test_fulfillment import CHEF_1_PHONE, create_confirmed_order, login_phone


def test_customer_cannot_access_control_room(login):
    response = login["client"].get(
        "/api/v1/admin/control-room/overview",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_refresh_detects_overdue_chef_acceptance_and_control_room_is_red_or_amber(login):
    client = login["client"]
    _, order, _ = create_confirmed_order(client, login, service_date=(date.today()+timedelta(days=40)).isoformat())
    chef = login_phone(client, CHEF_1_PHONE)
    assert client.get("/api/v1/chef/orders", headers=chef["headers"]).status_code == 200

    with SessionLocal() as db:
        fulfillment = db.get(
            ChefOrderFulfillmentEntity,
            UUID(order["id"]),
        )
        fulfillment.acceptance_deadline_at = utc_now() - timedelta(minutes=5)
        db.commit()

    headers, _ = admin_headers()
    refreshed = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=headers,
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["detected"] >= 1
    assert refreshed.json()["created"] >= 1

    incidents = client.get(
        "/api/v1/admin/control-room/incidents",
        params={"category": "chef_sla"},
        headers=headers,
    )
    assert incidents.status_code == 200
    incident = next(
        x
        for x in incidents.json()
        if x["source_id"] == order["id"]
    )
    assert incident["severity"] == "high"
    assert incident["status"] == "open"

    overview = client.get(
        "/api/v1/admin/control-room/overview",
        headers=headers,
    )
    assert overview.status_code == 200
    assert overview.json()["active_incidents"] >= 1
    assert overview.json()["health"] in {"amber", "red"}


def test_incident_acknowledge_escalate_resolve_and_audit(login):
    client = login["client"]
    _, order, _ = create_confirmed_order(client, login, service_date=(date.today()+timedelta(days=41)).isoformat())
    chef = login_phone(client, CHEF_1_PHONE)
    assert client.get("/api/v1/chef/orders", headers=chef["headers"]).status_code == 200

    with SessionLocal() as db:
        fulfillment = db.get(
            ChefOrderFulfillmentEntity,
            UUID(order["id"]),
        )
        fulfillment.acceptance_deadline_at = utc_now() - timedelta(minutes=5)
        db.commit()

    headers, admin_id = admin_headers()
    client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=headers,
    )
    incident = next(
        x
        for x in client.get(
            "/api/v1/admin/control-room/incidents",
            params={"category": "chef_sla"},
            headers=headers,
        ).json()
        if x["source_id"] == order["id"]
    )

    acknowledged = client.post(
        f"/api/v1/admin/control-room/incidents/{incident['id']}/acknowledge",
        headers=headers,
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"
    assert acknowledged.json()["owner_admin_id"] == str(admin_id)

    escalated = client.post(
        f"/api/v1/admin/control-room/incidents/{incident['id']}/escalate",
        headers=headers,
        json={"note": "Pilot operations escalation test"},
    )
    assert escalated.status_code == 200
    assert escalated.json()["severity"] == "critical"

    resolved = client.post(
        f"/api/v1/admin/control-room/incidents/{incident['id']}/resolve",
        headers=headers,
        json={"note": "Chef contacted and situation handled."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    audit = client.get(
        "/api/v1/admin/audit",
        headers=headers,
        params={"entity_type": "operations_incident"},
    )
    assert audit.status_code == 200
    actions = {x["action"] for x in audit.json()}
    assert "operations.incident.acknowledge" in actions
    assert "operations.incident.escalate" in actions
    assert "operations.incident.resolve" in actions


def test_incident_auto_resolves_when_condition_clears(login):
    client = login["client"]
    _, order, _ = create_confirmed_order(client, login, service_date=(date.today()+timedelta(days=42)).isoformat())
    chef = login_phone(client, CHEF_1_PHONE)
    assert client.get("/api/v1/chef/orders", headers=chef["headers"]).status_code == 200
    order_id = UUID(order["id"])

    with SessionLocal() as db:
        fulfillment = db.get(ChefOrderFulfillmentEntity, order_id)
        fulfillment.acceptance_deadline_at = utc_now() - timedelta(minutes=5)
        db.commit()

    headers, _ = admin_headers()
    client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=headers,
    )

    with SessionLocal() as db:
        fulfillment = db.get(ChefOrderFulfillmentEntity, order_id)
        fulfillment.stage = "accepted"
        fulfillment.accepted_at = utc_now()
        db.commit()

    refreshed = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=headers,
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["auto_resolved"] >= 1

    with SessionLocal() as db:
        incident = db.query(OperationsIncidentEntity).filter(
            OperationsIncidentEntity.fingerprint
            == f"chef_acceptance:{order_id}"
        ).one()
        assert incident.status == "resolved"
        assert incident.resolution_note == "auto_resolved_condition_cleared"


def test_urgent_support_sla_becomes_critical_incident(login):
    client = login["client"]
    customer_id = UUID(login["body"]["user"]["id"])

    with SessionLocal() as db:
        ticket = SupportTicketEntity(
            customer_id=customer_id,
            category="other",
            subject="Urgent pilot support",
            description="Needs immediate operations attention.",
            priority="urgent",
            status="new",
            created_at=utc_now() - timedelta(minutes=20),
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id

    headers, _ = admin_headers()
    refreshed = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=headers,
    )
    assert refreshed.status_code == 200

    incidents = client.get(
        "/api/v1/admin/control-room/incidents",
        params={"category": "support_sla"},
        headers=headers,
    ).json()
    incident = next(
        x for x in incidents if x["source_id"] == str(ticket_id)
    )
    assert incident["severity"] == "critical"


def test_launch_kpis_and_daily_brief_contract(login):
    client = login["client"]
    headers, _ = admin_headers()

    kpis = client.get(
        "/api/v1/admin/control-room/kpis",
        params={"days": 7},
        headers=headers,
    )
    assert kpis.status_code == 200
    body = kpis.json()
    assert body["days"] == 7
    for key in [
        "orders_created",
        "delivery_success_rate_pct",
        "cancellation_rate_pct",
        "repeat_customer_rate_pct",
        "average_chef_rating",
        "launch_target_rating_met",
        "launch_target_repeat_met",
        "launch_target_on_time_met",
        "launch_target_cancellation_met",
    ]:
        assert key in body

    brief = client.get(
        "/api/v1/admin/control-room/daily-brief",
        headers=headers,
    )
    assert brief.status_code == 200
    assert "actions" in brief.json()
    assert "available_drivers" in brief.json()
    assert "open_chefs" in brief.json()


def test_operations_scan_is_scheduled_as_worker_maintenance_job(client):
    with SessionLocal() as db:
        jobs = BackgroundJobService(
            db,
            get_settings(),
        ).schedule_maintenance()
        assert any(x.job_type == "operations.scan" for x in jobs)
        assert len(jobs) == 13
