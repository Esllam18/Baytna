import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    ChefProfileEntity,
    DriverProfileEntity,
    ReviewEntity,
    SupportMessageEntity,
    SupportTicketEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.payments.security import sign_webhook


CHEF_PHONE = "+201000000001"
DRIVER_PHONE = "+201090000001"


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
            phone=f"+20109{uuid4().int % 100000000:08d}",
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
        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "id": admin.id,
        }


def webhook(client, body: dict):
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    signature = sign_webhook(raw, get_settings().payment_webhook_secret)
    return client.post(
        "/api/v1/payments/webhooks/mock",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Baytna-Signature": signature,
        },
    )


def create_address(client, customer):
    response = client.post(
        "/api/v1/customer/addresses",
        headers=customer["headers"],
        json={
            "label": "المنزل",
            "area": "6 أكتوبر",
            "street": "شارع السنترال",
            "building": "10",
            "floor": "2",
            "apartment": "4",
            "is_default": True,
        },
    )
    assert response.status_code == 201


def create_delivered_order(client, customer, service_date: str):
    create_address(client, customer)
    chef = login_phone(client, CHEF_PHONE)

    client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    ).json()
    today = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [{
                "dish_id": signature[0]["id"],
                "quantity_total": 10,
                "max_per_order": 10,
            }],
        },
    ).json()

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer["headers"],
        json={
            "daily_menu_item_id": today["items"][0]["id"],
            "quantity": 1,
        },
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=customer["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=customer["headers"],
        json={"idempotency_key": f"post-order-pay-{order['id']}"},
    ).json()

    webhook(
        client,
        {
            "event_id": f"post-order-pay-success-{order['id']}",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )

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
    client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={},
    )

    driver = login_phone(client, DRIVER_PHONE)
    client.put(
        "/api/v1/driver/availability",
        headers=driver["headers"],
        json={"available": True},
    )
    task = next(
        x for x in client.get(
            "/api/v1/driver/missions/available",
            headers=driver["headers"],
        ).json()
        if x["order_id"] == order["id"]
    )
    client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver["headers"],
    )
    client.post(
        f"/api/v1/driver/missions/{task['id']}/arrive-pickup",
        headers=driver["headers"],
    )
    client.post(
        f"/api/v1/driver/missions/{task['id']}/confirm-pickup",
        headers=driver["headers"],
    )
    client.post(
        f"/api/v1/driver/missions/{task['id']}/start-delivery",
        headers=driver["headers"],
    )
    delivered = client.post(
        f"/api/v1/driver/missions/{task['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "otp",
            "proof_reference": "OTP-9988",
        },
    )
    assert delivered.status_code == 200
    return order, delivered.json()


def review_payload(chef_overall=5, delivery_overall=5):
    return {
        "food_quality": 5,
        "packaging": 4,
        "order_accuracy": 5,
        "value_for_money": 4,
        "chef_overall": chef_overall,
        "delivery_overall": delivery_overall,
        "comment": "الأكل ممتاز والتغليف كويس.",
    }


def test_review_requires_delivered_order(login):
    client = login["client"]
    response = client.post(
        "/api/v1/customer/orders/00000000-0000-0000-0000-000000000001/review",
        headers=login["headers"],
        json=review_payload(),
    )
    assert response.status_code == 404


def test_customer_can_review_delivered_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=80)).isoformat()
    order, task = create_delivered_order(client, login, service_date)

    response = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["order_id"] == order["id"]
    assert body["chef_overall"] == 5
    assert body["delivery_overall"] == 5
    assert body["driver_id"] == task["driver_id"]


def test_only_one_review_per_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=81)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    first = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(),
    )
    second = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(),
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "review_already_exists"


def test_review_updates_chef_and_driver_aggregate(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=82)).isoformat()
    order, task = create_delivered_order(client, login, service_date)

    client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(chef_overall=4, delivery_overall=3),
    )

    with SessionLocal() as db:
        chef = db.get(ChefProfileEntity, UUID("10000000-0000-0000-0000-000000000001"))
        driver = db.get(DriverProfileEntity, UUID(task["driver_id"]))
        assert chef.rating == 4.0
        assert driver.rating == 3.0

    summary = client.get(
        "/api/v1/chefs/10000000-0000-0000-0000-000000000001/rating-summary"
    )
    assert summary.status_code == 200
    assert summary.json()["rating"] == 4.0
    assert summary.json()["review_count"] == 1


def test_customer_can_update_own_review(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=83)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    created = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(chef_overall=4),
    ).json()

    updated = client.patch(
        f"/api/v1/customer/reviews/{created['id']}",
        headers=login["headers"],
        json={
            "chef_overall": 5,
            "comment": "بعد التواصل مع الدعم التجربة اتحسنت.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["chef_overall"] == 5


def test_hidden_review_not_in_public_or_aggregate(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=84)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    created = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(chef_overall=2),
    ).json()

    admin = create_admin_headers()
    moderated = client.patch(
        f"/api/v1/admin/reviews/{created['id']}/moderation",
        headers=admin["headers"],
        json={
            "is_visible": False,
            "moderation_note": "محتوى مخالف",
        },
    )
    assert moderated.status_code == 200
    assert moderated.json()["is_visible"] is False

    public = client.get(
        "/api/v1/chefs/10000000-0000-0000-0000-000000000001/reviews"
    )
    assert created["id"] not in {x["id"] for x in public.json()}

    summary = client.get(
        "/api/v1/chefs/10000000-0000-0000-0000-000000000001/rating-summary"
    )
    assert summary.json()["review_count"] == 0
    assert summary.json()["rating"] == 0.0


def test_customer_cannot_edit_another_customers_review(client):
    a = login_phone(client, "01090000001")
    b = login_phone(client, "01090000002")
    service_date = (date.today() + timedelta(days=85)).isoformat()
    order, _ = create_delivered_order(client, a, service_date)

    created = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=a["headers"],
        json=review_payload(),
    ).json()

    response = client.patch(
        f"/api/v1/customer/reviews/{created['id']}",
        headers=b["headers"],
        json={"comment": "محاولة غير مصرح بها"},
    )
    assert response.status_code == 404


def test_customer_can_create_order_linked_support_ticket(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=86)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    response = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "order_id": order["id"],
            "category": "food_quality",
            "subject": "مشكلة في جودة الأكل",
            "description": "الأكل وصل بارد وعايز أبلغ الدعم.",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["order_id"] == order["id"]
    assert len(body["messages"]) == 1
    assert body["messages"][0]["sender_role"] == "customer"


def test_customer_cannot_link_other_customers_order_to_ticket(client):
    a = login_phone(client, "01091110001")
    b = login_phone(client, "01091110002")
    service_date = (date.today() + timedelta(days=87)).isoformat()
    order, _ = create_delivered_order(client, a, service_date)

    response = client.post(
        "/api/v1/customer/support/tickets",
        headers=b["headers"],
        json={
            "order_id": order["id"],
            "category": "other",
            "subject": "طلب غير بتاعي",
            "description": "اختبار صلاحيات",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "order_not_found"


def test_admin_can_assign_and_investigate_ticket(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "app_issue",
            "subject": "مشكلة في التطبيق",
            "description": "التطبيق وقف أثناء الطلب.",
        },
    ).json()

    admin = create_admin_headers()
    assigned = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/assign",
        headers=admin["headers"],
        json={},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["assigned_admin_id"] == str(admin["id"])

    message = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers=admin["headers"],
        json={
            "body": "بنراجع المشكلة مع الفريق.",
            "is_internal": False,
        },
    )
    assert message.status_code == 200
    assert message.json()["status"] == "investigating"


def test_internal_admin_message_hidden_from_customer(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "other",
            "subject": "استفسار",
            "description": "عايز استفسر عن الطلب.",
        },
    ).json()

    admin = create_admin_headers()
    client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers=admin["headers"],
        json={
            "body": "ملاحظة داخلية لا تظهر للعميل",
            "is_internal": True,
        },
    )

    customer_view = client.get(
        f"/api/v1/customer/support/tickets/{ticket['id']}",
        headers=login["headers"],
    )
    assert customer_view.status_code == 200
    assert all(
        x["body"] != "ملاحظة داخلية لا تظهر للعميل"
        for x in customer_view.json()["messages"]
    )

    admin_view = client.get(
        f"/api/v1/admin/support/tickets/{ticket['id']}",
        headers=admin["headers"],
    )
    assert any(
        x["body"] == "ملاحظة داخلية لا تظهر للعميل"
        for x in admin_view.json()["messages"]
    )


def test_resolve_requires_resolution_details(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "payment",
            "subject": "مشكلة دفع",
            "description": "الخصم ظهر مرتين.",
        },
    ).json()
    admin = create_admin_headers()
    assigned = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/assign",
        headers=admin["headers"],
        json={},
    )
    assert assigned.status_code == 200

    response = client.patch(
        f"/api/v1/admin/support/tickets/{ticket['id']}/status",
        headers=admin["headers"],
        json={"status": "resolved"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "support_resolution_required"


def test_support_full_state_flow(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "missing_item",
            "subject": "صنف ناقص",
            "description": "في صنف ناقص من الطلب.",
            "priority": "urgent",
        },
    ).json()
    admin = create_admin_headers()

    client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/assign",
        headers=admin["headers"],
        json={},
    )

    investigating = client.patch(
        f"/api/v1/admin/support/tickets/{ticket['id']}/status",
        headers=admin["headers"],
        json={"status": "investigating"},
    )
    assert investigating.status_code == 200

    awaiting = client.patch(
        f"/api/v1/admin/support/tickets/{ticket['id']}/status",
        headers=admin["headers"],
        json={"status": "awaiting_customer"},
    )
    assert awaiting.status_code == 200

    customer_reply = client.post(
        f"/api/v1/customer/support/tickets/{ticket['id']}/messages",
        headers=login["headers"],
        json={"body": "أيوه، الصنف الناقص كان السلطة."},
    )
    assert customer_reply.status_code == 200
    assert customer_reply.json()["status"] == "investigating"

    resolved = client.patch(
        f"/api/v1/admin/support/tickets/{ticket['id']}/status",
        headers=admin["headers"],
        json={
            "status": "resolved",
            "resolution_code": "credit_issued",
            "resolution_note": "تم تعويض العميل.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None

    closed = client.patch(
        f"/api/v1/admin/support/tickets/{ticket['id']}/status",
        headers=admin["headers"],
        json={"status": "closed"},
    )
    assert closed.status_code == 200
    assert closed.json()["closed_at"] is not None


def test_closed_ticket_rejects_new_customer_message(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "other",
            "subject": "اختبار إغلاق",
            "description": "تذكرة للاختبار.",
        },
    ).json()
    admin = create_admin_headers()

    client.patch(
        f"/api/v1/admin/support/tickets/{ticket['id']}/status",
        headers=admin["headers"],
        json={"status": "closed"},
    )

    response = client.post(
        f"/api/v1/customer/support/tickets/{ticket['id']}/messages",
        headers=login["headers"],
        json={"body": "رسالة بعد الإغلاق"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "support_ticket_closed"


def test_customer_cannot_use_admin_support(login):
    response = login["client"].get(
        "/api/v1/admin/support/tickets",
        headers=login["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
