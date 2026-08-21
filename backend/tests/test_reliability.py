import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    AuthSessionEntity,
    BackgroundJobEntity,
    InventoryReservationEntity,
    OtpChallengeEntity,
    OutboxEventEntity,
    PaymentEntity,
    SpecialOrderRequestEntity,
    UserEntity,
    WorkerHeartbeatEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token, hash_secret, utc_now
from app.modules.reliability.jobs import BackgroundJobService
from app.modules.reliability.outbox import OutboxPublisher, OutboxService
from app.modules.reliability.worker import WorkerService
from app.modules.payments.security import sign_webhook

CHEF_PHONE = "+201000000001"
DRIVER_PHONE = "+201090000001"


def login_phone(client, phone: str):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert sent.status_code == 200
    otp = sent.json()["development_otp"]
    verified = client.post("/api/v1/auth/verify-otp", json={"phone": phone, "code": otp})
    assert verified.status_code == 200
    body = verified.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}, "body": body}


def admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        user = UserEntity(id=uuid4(), phone=f"+20107{uuid4().int % 100000000:08d}", role="admin", is_active=True)
        db.add(user); db.commit(); db.refresh(user)
        token, _ = create_access_token(user_id=user.id, role=UserRole.ADMIN, settings=settings)
        return {"Authorization": f"Bearer {token}"}


def signed_webhook(client, body: dict):
    raw = json.dumps(body, separators=(",", ":")).encode()
    sig = sign_webhook(raw, get_settings().payment_webhook_secret)
    return client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw,
        headers={"Content-Type": "application/json", "X-Baytna-Signature": sig},
    )


def prepare_pending_order(client, customer, service_date: str):
    chef = login_phone(client, CHEF_PHONE)
    client.post("/api/v1/chef/workdays/open", headers=chef["headers"], json={"service_date": service_date})
    signature = client.get("/api/v1/chef/signature-menu", headers=chef["headers"]).json()
    today = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={"service_date": service_date, "items": [{"dish_id": signature[0]["id"], "quantity_total": 5, "max_per_order": 5}]},
    ).json()
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer["headers"],
        json={"daily_menu_item_id": today["items"][0]["id"], "quantity": 2},
    ).json()
    order = client.post(
        "/api/v1/customer/orders",
        headers=customer["headers"],
        json={"cart_id": cart["id"]},
    ).json()
    return chef, today["items"][0], order


def test_outbox_enqueue_is_idempotent(client):
    with SessionLocal() as db:
        svc = OutboxService(db, get_settings())
        a = svc.enqueue(event_type="test.event", aggregate_type="test", aggregate_id="1", payload={"x": 1}, dedupe_key="test.event:1")
        b = svc.enqueue(event_type="test.event", aggregate_type="test", aggregate_id="1", payload={"x": 1}, dedupe_key="test.event:1")
        db.commit()
        assert a.id == b.id
        assert len(list(db.scalars(select(OutboxEventEntity)).all())) == 1


def test_payment_success_writes_transactional_outbox(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=100)).isoformat()
    _, _, order = prepare_pending_order(client, login, service_date)
    payment = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"], json={"idempotency_key": "rel-payment-0001"},
    ).json()
    response = signed_webhook(client, {
        "event_id": "evt-rel-payment-001", "event_type": "payment.succeeded",
        "payment_reference": payment["provider_reference"], "amount_minor": payment["amount_minor"], "currency": "EGP",
    })
    assert response.status_code == 200
    with SessionLocal() as db:
        types = {x.event_type for x in db.scalars(select(OutboxEventEntity)).all()}
        assert "payment.succeeded" in types
        assert "order.confirmed" in types


def test_support_ticket_writes_outbox(login):
    response = login["client"].post(
        "/api/v1/customer/support/tickets", headers=login["headers"],
        json={"category": "other", "subject": "اختبار outbox", "description": "تفاصيل الاختبار"},
    )
    assert response.status_code == 201
    with SessionLocal() as db:
        row = db.scalar(select(OutboxEventEntity).where(OutboxEventEntity.event_type == "support.ticket.created"))
        assert row is not None
        assert row.status == "pending"


class RecordingPublisher(OutboxPublisher):
    def __init__(self): self.ids = []
    def publish(self, event): self.ids.append(event.id)


class FailingPublisher(OutboxPublisher):
    def publish(self, event): raise RuntimeError("publisher down")


def test_outbox_publisher_marks_event_published(client):
    with SessionLocal() as db:
        svc = OutboxService(db, get_settings())
        event = svc.enqueue(event_type="x", aggregate_type="a", aggregate_id="1", payload={}, dedupe_key="publish-once")
        db.commit()
        publisher = RecordingPublisher()
        result = svc.publish_due(worker_id="w1", publisher=publisher, limit=10)
        assert result == {"published": 1, "failed": 0}
        db.refresh(event)
        assert event.status == "published"
        assert event.published_at is not None
        assert publisher.ids == [event.id]


def test_outbox_failure_retries_then_dead_letters(client):
    settings = get_settings()
    with SessionLocal() as db:
        svc = OutboxService(db, settings)
        event = svc.enqueue(event_type="x", aggregate_type="a", aggregate_id="2", payload={}, dedupe_key="fail-dead", max_attempts=2)
        db.commit()
        svc.publish_due(worker_id="w1", publisher=FailingPublisher(), limit=1)
        db.refresh(event)
        assert event.status == "retry"
        event.available_at = utc_now() - timedelta(seconds=1); db.commit()
        svc.publish_due(worker_id="w1", publisher=FailingPublisher(), limit=1)
        db.refresh(event)
        assert event.status == "dead_letter"
        assert event.attempts == 2


def test_background_job_enqueue_is_idempotent(client):
    with SessionLocal() as db:
        svc = BackgroundJobService(db, get_settings())
        a = svc.enqueue(job_type="maintenance.cleanup_auth", idempotency_key="job-idem")
        b = svc.enqueue(job_type="maintenance.cleanup_auth", idempotency_key="job-idem")
        db.commit()
        assert a.id == b.id
        assert len(list(db.scalars(select(BackgroundJobEntity)).all())) == 1


def test_worker_schedules_and_executes_maintenance(client):
    with SessionLocal() as db:
        result = WorkerService(db, get_settings()).run_once(worker_id="test-worker")
        assert result["jobs"]["succeeded"] >= 4
        heartbeat = db.get(WorkerHeartbeatEntity, "test-worker")
        assert heartbeat is not None
        assert heartbeat.status == "idle"
        assert heartbeat.processed_jobs >= 4


def test_expired_inventory_hold_is_released_by_job(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=101)).isoformat()
    _, menu_item, order = prepare_pending_order(client, login, service_date)
    with SessionLocal() as db:
        reservation = db.scalar(select(InventoryReservationEntity).where(InventoryReservationEntity.order_id == UUID(order["id"])))
        reservation.expires_at = utc_now() - timedelta(minutes=1)
        job = BackgroundJobService(db, get_settings()).enqueue(job_type="maintenance.release_expired_holds", idempotency_key="expire-hold-test")
        db.commit()
        BackgroundJobService(db, get_settings()).run_due(worker_id="w", limit=1)
        db.refresh(reservation)
        assert reservation.status == "expired"
        order_row = db.get(__import__('app.core.db_models', fromlist=['OrderEntity']).OrderEntity, UUID(order["id"]))
        assert order_row.status == "expired"


def test_auth_cleanup_job_deletes_expired_rows(client):
    with SessionLocal() as db:
        now = utc_now()
        challenge = OtpChallengeEntity(phone="01012345678", code_hash="x"*64, expires_at=now - timedelta(seconds=1), attempts=0)
        user = UserEntity(phone="01012345679", role="customer", is_active=True)
        db.add_all([challenge, user]); db.flush()
        session = AuthSessionEntity(user_id=user.id, refresh_token_hash="y"*64, expires_at=now - timedelta(seconds=1))
        db.add(session); db.commit()
        svc = BackgroundJobService(db, get_settings())
        svc.enqueue(job_type="maintenance.cleanup_auth", idempotency_key="cleanup-auth-test"); db.commit()
        svc.run_due(worker_id="w", limit=1)
        assert db.get(OtpChallengeEntity, challenge.id) is None
        assert db.get(AuthSessionEntity, session.id) is None


def test_pending_payment_expiry_job_marks_payment_expired(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=102)).isoformat()
    _, _, order = prepare_pending_order(client, login, service_date)
    payment = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent", headers=login["headers"], json={"idempotency_key": "expire-payment-test"}
    ).json()
    with SessionLocal() as db:
        row = db.get(PaymentEntity, UUID(payment["id"]))
        row.expires_at = utc_now() - timedelta(seconds=1)
        svc = BackgroundJobService(db, get_settings())
        svc.enqueue(job_type="maintenance.expire_pending_payments", idempotency_key="payment-expiry-job"); db.commit()
        svc.run_due(worker_id="w", limit=1)
        db.refresh(row)
        assert row.status == "expired"


def test_stale_job_lock_is_recovered(client):
    with SessionLocal() as db:
        svc = BackgroundJobService(db, get_settings())
        row = svc.enqueue(job_type="maintenance.cleanup_auth", idempotency_key="stale-job")
        row.status = "running"; row.locked_at = utc_now() - timedelta(hours=1); row.locked_by = "dead-worker"
        db.commit()
        recovered = svc.recover_stale()
        db.refresh(row)
        assert recovered == 1
        assert row.status == "retry"
        assert row.locked_by is None


def test_stale_outbox_lock_is_recovered(client):
    with SessionLocal() as db:
        svc = OutboxService(db, get_settings())
        row = svc.enqueue(event_type="x", aggregate_type="a", aggregate_id="3", payload={}, dedupe_key="stale-outbox")
        row.status = "processing"; row.locked_at = utc_now() - timedelta(hours=1); row.locked_by = "dead-worker"
        db.commit()
        recovered = svc.recover_stale(stale_seconds=10)
        db.refresh(row)
        assert recovered == 1
        assert row.status == "retry"


def test_admin_reliability_requires_admin(login):
    response = login["client"].get("/api/v1/admin/reliability/summary", headers=login["headers"])
    assert response.status_code == 403


def test_admin_can_view_reliability_summary(client):
    headers = admin_headers()
    response = client.get("/api/v1/admin/reliability/summary", headers=headers)
    assert response.status_code == 200
    assert "outbox" in response.json() and "jobs" in response.json() and "workers" in response.json()


def test_admin_can_retry_dead_letter_outbox(client):
    headers = admin_headers()
    with SessionLocal() as db:
        row = OutboxService(db, get_settings()).enqueue(event_type="x", aggregate_type="a", aggregate_id="4", payload={}, dedupe_key="admin-retry-outbox")
        row.status = "dead_letter"; row.attempts = 8; row.last_error = "boom"; db.commit(); event_id = row.id
    response = client.post(f"/api/v1/admin/reliability/outbox/{event_id}/retry", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["attempts"] == 0


def test_admin_can_retry_dead_letter_job(client):
    headers = admin_headers()
    with SessionLocal() as db:
        row = BackgroundJobService(db, get_settings()).enqueue(job_type="maintenance.cleanup_auth", idempotency_key="admin-retry-job")
        row.status = "dead_letter"; row.attempts = 5; row.last_error = "boom"; db.commit(); job_id = row.id
    response = client.post(f"/api/v1/admin/reliability/jobs/{job_id}/retry", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["attempts"] == 0


def test_health_ready_reports_dead_letter_counts(client):
    response = client.get("/health/reliability")
    assert response.status_code == 200
    body = response.json()
    assert "outbox_dead_letter" in body
    assert "jobs_dead_letter" in body
