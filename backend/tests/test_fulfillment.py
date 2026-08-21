import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    DailyMenuItemEntity,
    PaymentEntity,
    RefundEntity,
)
from app.modules.payments.security import sign_webhook


CHEF_1_ID = "10000000-0000-0000-0000-000000000001"
CHEF_2_ID = "10000000-0000-0000-0000-000000000002"
CHEF_1_PHONE = "+201000000001"
CHEF_2_PHONE = "+201000000002"


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


def publish_today_item(
    client,
    chef_phone: str,
    service_date: str,
    quantity=10,
):
    chef = login_phone(client, chef_phone)

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
                    "quantity_total": quantity,
                    "max_per_order": 10,
                }
            ],
        },
    )
    assert published.status_code == 200
    return published.json()["items"][0]


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


def create_confirmed_order(
    client,
    customer,
    *,
    chef_phone=CHEF_1_PHONE,
    service_date: str,
    quantity=2,
    stock=10,
):
    menu_item = publish_today_item(
        client,
        chef_phone,
        service_date,
        quantity=stock,
    )

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
    order = order.json()

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=customer["headers"],
        json={"idempotency_key": f"fulfillment-pay-{order['id']}"},
    )
    assert intent.status_code == 201
    intent = intent.json()

    success = webhook(
        client,
        {
            "event_id": f"evt-confirm-{order['id']}",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )
    assert success.status_code == 200

    return menu_item, order, intent


def test_confirmed_order_appears_in_correct_chef_queue(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=40)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )

    chef1 = login_phone(client, CHEF_1_PHONE)
    chef2 = login_phone(client, CHEF_2_PHONE)

    queue1 = client.get(
        "/api/v1/chef/orders",
        headers=chef1["headers"],
    )
    assert queue1.status_code == 200
    assert order["id"] in {x["order_id"] for x in queue1.json()}
    found = next(x for x in queue1.json() if x["order_id"] == order["id"])
    assert found["order_status"] == "confirmed"
    assert found["fulfillment_stage"] == "new"
    assert found["acceptance_deadline_at"] is not None

    queue2 = client.get(
        "/api/v1/chef/orders",
        headers=chef2["headers"],
    )
    assert queue2.status_code == 200
    assert order["id"] not in {x["order_id"] for x in queue2.json()}


def test_customer_cannot_use_chef_order_queue(login):
    response = login["client"].get(
        "/api/v1/chef/orders",
        headers=login["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_chef_accepts_confirmed_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=41)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    eta = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={
            "estimated_ready_at": eta,
            "chef_note": "هنجهز الطلب في أسرع وقت.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["order_status"] == "accepted_by_chef"
    assert body["fulfillment_stage"] == "accepted"
    assert body["accepted_at"] is not None
    assert body["estimated_ready_at"] is not None


def test_accept_is_idempotent(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=42)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    payload = {"chef_note": "تم القبول"}
    first = client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json=payload,
    )
    second = client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["order_status"] == "accepted_by_chef"


def test_cannot_start_preparing_before_accept(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=43)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    response = client.post(
        f"/api/v1/chef/orders/{order['id']}/start-preparing",
        headers=chef["headers"],
        json={},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "fulfillment_missing"


def test_full_preparation_workflow_updates_customer_tracking(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=44)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    accepted = client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={},
    )
    assert accepted.status_code == 200

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "الشيف بدأت تجهيز أكلك"

    preparing = client.post(
        f"/api/v1/chef/orders/{order['id']}/start-preparing",
        headers=chef["headers"],
        json={"chef_note": "بدأنا الطبخ"},
    )
    assert preparing.status_code == 200
    assert preparing.json()["order_status"] == "preparing"
    assert preparing.json()["fulfillment_stage"] == "preparing"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "جاري الطبخ"

    packaging = client.post(
        f"/api/v1/chef/orders/{order['id']}/start-packaging",
        headers=chef["headers"],
        json={"chef_note": "جاري التغليف"},
    )
    assert packaging.status_code == 200
    assert packaging.json()["order_status"] == "preparing"
    assert packaging.json()["fulfillment_stage"] == "packaging"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "جاري التغليف"

    ready = client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={},
    )
    assert ready.status_code == 200
    assert ready.json()["order_status"] == "ready_for_pickup"
    assert ready.json()["fulfillment_stage"] == "ready"
    assert ready.json()["ready_at"] is not None

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "أكلك جاهز"


def test_ready_for_pickup_is_idempotent(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=45)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={},
    )
    client.post(
        f"/api/v1/chef/orders/{order['id']}/start-preparing",
        headers=chef["headers"],
        json={},
    )

    first = client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={},
    )
    second = client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["order_status"] == "ready_for_pickup"


def test_chef_rejection_refunds_and_cancels_paid_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=46)).isoformat()
    menu_item, order, intent = create_confirmed_order(
        client,
        login,
        service_date=service_date,
        quantity=3,
        stock=5,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    rejected = client.post(
        f"/api/v1/chef/orders/{order['id']}/reject",
        headers=chef["headers"],
        json={"reason": "تعذر تنفيذ الطلب اليوم"},
    )
    assert rejected.status_code == 200
    body = rejected.json()
    assert body["order_status"] == "cancelled"
    assert body["fulfillment_stage"] == "rejected"
    assert body["rejection_reason"] == "تعذر تنفيذ الطلب اليوم"

    payment = client.get(
        f"/api/v1/customer/orders/{order['id']}/payment",
        headers=login["headers"],
    )
    assert payment.status_code == 200
    assert payment.json()["refunded_minor"] == intent["amount_minor"]

    with SessionLocal() as db:
        refund = db.scalar(
            select(RefundEntity).where(
                RefundEntity.order_id == UUID(order["id"])
            )
        )
        assert refund is not None
        assert refund.status == "succeeded"
        assert refund.amount_minor == intent["amount_minor"]

        item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert item.quantity_available == 5


def test_rejection_is_idempotent_and_does_not_double_refund(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=47)).isoformat()
    _, order, intent = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    payload = {"reason": "إغلاق طارئ للمطبخ"}
    first = client.post(
        f"/api/v1/chef/orders/{order['id']}/reject",
        headers=chef["headers"],
        json=payload,
    )
    second = client.post(
        f"/api/v1/chef/orders/{order['id']}/reject",
        headers=chef["headers"],
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    with SessionLocal() as db:
        refunds = list(
            db.scalars(
                select(RefundEntity).where(
                    RefundEntity.order_id == UUID(order["id"])
                )
            ).all()
        )
        assert len(refunds) == 1
        payment = db.get(PaymentEntity, UUID(intent["id"]))
        assert payment.refunded_minor == payment.amount_minor


def test_cannot_reject_after_accept(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=48)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={},
    )

    response = client.post(
        f"/api/v1/chef/orders/{order['id']}/reject",
        headers=chef["headers"],
        json={"reason": "محاولة رفض بعد القبول"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "order_cannot_reject"


def test_other_chef_cannot_read_or_transition_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=49)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    other = login_phone(client, CHEF_2_PHONE)

    detail = client.get(
        f"/api/v1/chef/orders/{order['id']}",
        headers=other["headers"],
    )
    assert detail.status_code == 404

    accept = client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=other["headers"],
        json={},
    )
    assert accept.status_code == 404


def test_queue_can_filter_by_stage(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=50)).isoformat()
    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    client.get("/api/v1/chef/orders", headers=chef["headers"])

    new_queue = client.get(
        "/api/v1/chef/orders",
        params={"stage": "new"},
        headers=chef["headers"],
    )
    assert order["id"] in {x["order_id"] for x in new_queue.json()}

    client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={},
    )

    accepted_queue = client.get(
        "/api/v1/chef/orders",
        params={"stage": "accepted"},
        headers=chef["headers"],
    )
    assert order["id"] in {x["order_id"] for x in accepted_queue.json()}


def test_customer_cannot_track_another_customers_order(client):
    customer_a = login_phone(client, "01055550001")
    customer_b = login_phone(client, "01055550002")
    service_date = (date.today() + timedelta(days=51)).isoformat()

    _, order, _ = create_confirmed_order(
        client,
        customer_a,
        service_date=service_date,
    )

    response = client.get(
        f"/api/v1/customer/orders/{order['id']}/tracking",
        headers=customer_b["headers"],
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "order_not_found"
