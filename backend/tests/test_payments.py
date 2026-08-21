import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    InventoryReservationEntity,
    OrderEntity,
    PaymentEntity,
    PaymentWebhookEventEntity,
    RefundEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.payments.security import sign_webhook


CHEF_1_ID = "10000000-0000-0000-0000-000000000001"
CHEF_1_PHONE = "+201000000001"


def login_phone(client, phone: str):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert sent.status_code == 200
    otp = sent.json()["development_otp"]

    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": phone, "code": otp},
    )
    assert verified.status_code == 200
    body = verified.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "body": body,
    }


def create_admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        admin = UserEntity(
            id=uuid4(),
            phone="+201099999999",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        token, _ = create_access_token(
            user_id=admin.id,
            role=UserRole.ADMIN,
            settings=settings,
        )
        return {"Authorization": f"Bearer {token}"}


def publish_today_item(client, service_date: str, quantity=10):
    chef = login_phone(client, CHEF_1_PHONE)

    opened = client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    assert opened.status_code == 200

    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    )
    dish_id = signature.json()[0]["id"]

    published = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {
                    "dish_id": dish_id,
                    "quantity_total": quantity,
                    "max_per_order": 10,
                }
            ],
        },
    )
    assert published.status_code == 200
    return published.json()["items"][0]


def create_pending_order(client, customer, service_date: str, quantity=2, stock=10):
    menu_item = publish_today_item(client, service_date, quantity=stock)

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": quantity,
        },
    )
    assert cart.status_code == 201

    order = client.post(
        "/api/v1/customer/orders",
        headers=customer["headers"],
        json={"cart_id": cart.json()["id"]},
    )
    assert order.status_code == 201

    return menu_item, order.json()


def webhook(client, body: dict):
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    signature = sign_webhook(
        raw,
        get_settings().payment_webhook_secret,
    )
    return client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Baytna-Signature": signature,
        },
    )


def test_create_payment_intent_for_pending_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=20)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    response = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-intent-0001"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["order_id"] == order["id"]
    assert body["status"] == "pending"
    assert body["provider"] == "mock"
    assert body["checkout_url"].startswith("https://mock-payments.local/")
    assert body["amount_minor"] == order["total_minor"]


def test_payment_intent_is_idempotent(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=21)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    payload = {"idempotency_key": "payment-intent-idempotent-001"}
    first = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json=payload,
    )
    second = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json=payload,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_invalid_webhook_signature_is_rejected(login):
    client = login["client"]
    response = client.post(
        "/api/v1/payments/webhooks/mock",
        content=b'{"event_id":"evt1","event_type":"payment.succeeded","payment_reference":"x"}',
        headers={
            "Content-Type": "application/json",
            "X-Baytna-Signature": "bad-signature",
        },
    )
    assert response.status_code == 401
    assert (
        response.json()["error"]["code"]
        == "payment_webhook_signature_invalid"
    )


def test_success_webhook_confirms_order_and_converts_reservation(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=22)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-success-0001"},
    ).json()

    response = webhook(
        client,
        {
            "event_id": "evt-payment-success-0001",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    detail = client.get(
        f"/api/v1/customer/orders/{order['id']}",
        headers=login["headers"],
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "confirmed"
    assert detail.json()["inventory_hold_expires_at"] is None
    assert detail.json()["timeline"][-1]["to_status"] == "confirmed"

    with SessionLocal() as db:
        payment = db.get(PaymentEntity, UUID(intent["id"]))
        assert payment.status == "succeeded"

        reservation = db.scalar(
            select(InventoryReservationEntity).where(
                InventoryReservationEntity.order_id == UUID(order["id"])
            )
        )
        assert reservation.status == "converted"


def test_duplicate_success_webhook_is_idempotent(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=23)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-success-idempotent"},
    ).json()

    body = {
        "event_id": "evt-duplicate-0001",
        "event_type": "payment.succeeded",
        "payment_reference": intent["provider_reference"],
        "amount_minor": intent["amount_minor"],
        "currency": "EGP",
    }
    first = webhook(client, body)
    second = webhook(client, body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    with SessionLocal() as db:
        count = len(
            list(
                db.scalars(
                    select(PaymentWebhookEventEntity).where(
                        PaymentWebhookEventEntity.provider_event_id
                        == "evt-duplicate-0001"
                    )
                ).all()
            )
        )
        assert count == 1


def test_failed_payment_releases_inventory_and_expires_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=24)).isoformat()
    menu_item, order = create_pending_order(
        client,
        login,
        service_date,
        quantity=3,
        stock=5,
    )

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-failure-0001"},
    ).json()

    response = webhook(
        client,
        {
            "event_id": "evt-payment-failed-0001",
            "event_type": "payment.failed",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )
    assert response.status_code == 200

    detail = client.get(
        f"/api/v1/customer/orders/{order['id']}",
        headers=login["headers"],
    )
    assert detail.json()["status"] == "expired"
    assert detail.json()["timeline"][-1]["reason"] == "payment_failed"

    with SessionLocal() as db:
        from app.core.db_models import DailyMenuItemEntity
        db_item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert db_item.quantity_available == 5


def test_webhook_amount_mismatch_is_rejected(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=25)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-mismatch-0001"},
    ).json()

    response = webhook(
        client,
        {
            "event_id": "evt-payment-mismatch-0001",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"] + 1,
            "currency": "EGP",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "payment_amount_mismatch"


def test_customer_can_read_payment_status(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=26)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    created = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-read-0001"},
    )
    assert created.status_code == 201

    read = client.get(
        f"/api/v1/customer/orders/{order['id']}/payment",
        headers=login["headers"],
    )
    assert read.status_code == 200
    assert read.json()["id"] == created.json()["id"]


def test_admin_can_partially_refund_confirmed_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=27)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-refund-0001"},
    ).json()

    success = webhook(
        client,
        {
            "event_id": "evt-refund-success-payment",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )
    assert success.status_code == 200

    admin_headers = create_admin_headers()
    refund_amount = max(1, intent["amount_minor"] // 2)

    refund = client.post(
        f"/api/v1/admin/orders/{order['id']}/refunds",
        headers=admin_headers,
        json={
            "amount_minor": refund_amount,
            "reason": "تعويض جزئي للعميل",
            "idempotency_key": "refund-partial-0001",
        },
    )
    assert refund.status_code == 201
    assert refund.json()["status"] == "succeeded"
    assert refund.json()["amount_minor"] == refund_amount

    payment = client.get(
        f"/api/v1/customer/orders/{order['id']}/payment",
        headers=login["headers"],
    )
    assert payment.json()["refunded_minor"] == refund_amount


def test_refund_cannot_exceed_remaining_amount(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=28)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-refund-limit-001"},
    ).json()

    webhook(
        client,
        {
            "event_id": "evt-refund-limit-payment",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )

    admin_headers = create_admin_headers()
    response = client.post(
        f"/api/v1/admin/orders/{order['id']}/refunds",
        headers=admin_headers,
        json={
            "amount_minor": intent["amount_minor"] + 1,
            "reason": "قيمة أكبر من المدفوع",
            "idempotency_key": "refund-too-large-001",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "refund_exceeds_remaining"


def test_customer_cannot_call_admin_refund(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=29)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    response = client.post(
        f"/api/v1/admin/orders/{order['id']}/refunds",
        headers=login["headers"],
        json={
            "amount_minor": 100,
            "reason": "غير مسموح",
            "idempotency_key": "refund-customer-denied",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_refund_request_is_idempotent(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=30)).isoformat()
    _, order = create_pending_order(client, login, service_date)

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "payment-refund-idempotent"},
    ).json()

    webhook(
        client,
        {
            "event_id": "evt-refund-idempotent-payment",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )

    admin_headers = create_admin_headers()
    payload = {
        "amount_minor": intent["amount_minor"],
        "reason": "استرداد كامل مكرر",
        "idempotency_key": "refund-idempotent-0001",
    }
    first = client.post(
        f"/api/v1/admin/orders/{order['id']}/refunds",
        headers=admin_headers,
        json=payload,
    )
    second = client.post(
        f"/api/v1/admin/orders/{order['id']}/refunds",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
