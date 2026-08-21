import json
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    LoyaltyAccountEntity,
    LoyaltyTransactionEntity,
    NotificationEntity,
)
from app.modules.payments.security import sign_webhook


CHEF_ID = "10000000-0000-0000-0000-000000000001"
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


def prepare_order(client, customer, service_date: str):
    client.post(
        "/api/v1/customer/addresses",
        headers=customer["headers"],
        json={
            "label": "المنزل",
            "area": "6 أكتوبر",
            "street": "شارع الحصري",
            "building": "5",
            "floor": "2",
            "apartment": "8",
            "is_default": True,
        },
    )

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
            "quantity": 2,
        },
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=customer["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    return chef, signature[0], order


def pay_and_ready(client, customer, chef, order):
    intent = client.post(
        f"/api/v1/customer/orders/{order['id']}/payment-intent",
        headers=customer["headers"],
        json={"idempotency_key": f"retention-pay-{order['id']}"},
    ).json()

    success = webhook(
        client,
        {
            "event_id": f"retention-payment-success-{order['id']}",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )
    assert success.status_code == 200

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
    ready = client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={},
    )
    assert ready.status_code == 200
    return intent


def deliver_order(client, customer, order):
    driver = login_phone(client, DRIVER_PHONE)
    available = client.put(
        "/api/v1/driver/availability",
        headers=driver["headers"],
        json={"available": True},
    )
    assert available.status_code == 200

    task = next(
        x
        for x in client.get(
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
            "proof_reference": "OTP-2323",
        },
    )
    assert delivered.status_code == 200
    return delivered.json()


def test_customer_can_favorite_chef_and_operation_is_idempotent(login):
    client = login["client"]

    first = client.put(
        f"/api/v1/customer/favorites/chefs/{CHEF_ID}",
        headers=login["headers"],
    )
    second = client.put(
        f"/api/v1/customer/favorites/chefs/{CHEF_ID}",
        headers=login["headers"],
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["favorite_id"] == second.json()["favorite_id"]

    listing = client.get(
        "/api/v1/customer/favorites/chefs",
        headers=login["headers"],
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["chef_id"] == CHEF_ID


def test_customer_can_remove_favorite_chef(login):
    client = login["client"]
    client.put(
        f"/api/v1/customer/favorites/chefs/{CHEF_ID}",
        headers=login["headers"],
    )

    removed = client.delete(
        f"/api/v1/customer/favorites/chefs/{CHEF_ID}",
        headers=login["headers"],
    )
    assert removed.status_code == 204

    listing = client.get(
        "/api/v1/customer/favorites/chefs",
        headers=login["headers"],
    )
    assert listing.json() == []


def test_customer_can_favorite_signature_dish(login):
    client = login["client"]
    signature = client.get(
        f"/api/v1/chefs/{CHEF_ID}/signature-menu",
    ).json()
    dish_id = signature[0]["id"]

    added = client.put(
        f"/api/v1/customer/favorites/dishes/{dish_id}",
        headers=login["headers"],
    )
    assert added.status_code == 200
    assert added.json()["dish_id"] == dish_id
    assert added.json()["chef_id"] == CHEF_ID

    summary = client.get(
        "/api/v1/customer/favorites/summary",
        headers=login["headers"],
    )
    assert summary.json()["dishes_count"] == 1


def test_favorites_are_isolated_between_customers(client):
    a = login_phone(client, "01070000001")
    b = login_phone(client, "01070000002")

    client.put(
        f"/api/v1/customer/favorites/chefs/{CHEF_ID}",
        headers=a["headers"],
    )

    b_list = client.get(
        "/api/v1/customer/favorites/chefs",
        headers=b["headers"],
    )
    assert b_list.status_code == 200
    assert b_list.json() == []


def test_payment_success_emits_order_confirmed_notification(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=90)).isoformat()
    chef, _, order = prepare_order(client, login, service_date)
    pay_and_ready(client, login, chef, order)

    notifications = client.get(
        "/api/v1/customer/notifications",
        headers=login["headers"],
    )
    assert notifications.status_code == 200
    kinds = {x["kind"] for x in notifications.json()}
    assert "order_confirmed" in kinds
    assert "chef_accepted" in kinds
    assert "order_ready" in kinds


def test_notifications_can_be_marked_read(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=91)).isoformat()
    chef, _, order = prepare_order(client, login, service_date)
    pay_and_ready(client, login, chef, order)

    summary = client.get(
        "/api/v1/customer/notifications/summary",
        headers=login["headers"],
    )
    assert summary.status_code == 200
    assert summary.json()["unread_count"] >= 3

    notification_id = summary.json()["latest"][0]["id"]
    marked = client.post(
        f"/api/v1/customer/notifications/{notification_id}/read",
        headers=login["headers"],
    )
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    all_read = client.post(
        "/api/v1/customer/notifications/read-all",
        headers=login["headers"],
    )
    assert all_read.status_code == 200

    summary = client.get(
        "/api/v1/customer/notifications/summary",
        headers=login["headers"],
    )
    assert summary.json()["unread_count"] == 0


def test_notification_ownership_is_enforced(client):
    a = login_phone(client, "01070000101")
    b = login_phone(client, "01070000102")
    service_date = (date.today() + timedelta(days=92)).isoformat()
    chef, _, order = prepare_order(client, a, service_date)
    pay_and_ready(client, a, chef, order)

    note = client.get(
        "/api/v1/customer/notifications",
        headers=a["headers"],
    ).json()[0]

    response = client.post(
        f"/api/v1/customer/notifications/{note['id']}/read",
        headers=b["headers"],
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "notification_not_found"


def test_delivery_awards_loyalty_points_once(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=93)).isoformat()
    chef, _, order = prepare_order(client, login, service_date)
    pay_and_ready(client, login, chef, order)
    delivered = deliver_order(client, login, order)

    account = client.get(
        "/api/v1/customer/loyalty",
        headers=login["headers"],
    )
    assert account.status_code == 200
    body = account.json()

    expected = order["total_minor"] // get_settings().loyalty_minor_per_point
    assert body["balance_points"] == expected
    assert body["lifetime_earned_points"] == expected
    assert len(body["transactions"]) == 1
    assert body["transactions"][0]["source_order_id"] == order["id"]

    # Idempotent delivery endpoint must not double-credit loyalty.
    driver = login_phone(client, DRIVER_PHONE)
    repeat = client.post(
        f"/api/v1/driver/missions/{delivered['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "otp",
            "proof_reference": "OTP-2323",
        },
    )
    assert repeat.status_code == 200

    account2 = client.get(
        "/api/v1/customer/loyalty",
        headers=login["headers"],
    ).json()
    assert account2["balance_points"] == expected
    assert len(account2["transactions"]) == 1


def test_delivered_order_emits_notification_and_loyalty_transaction(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=94)).isoformat()
    chef, _, order = prepare_order(client, login, service_date)
    pay_and_ready(client, login, chef, order)
    deliver_order(client, login, order)

    notes = client.get(
        "/api/v1/customer/notifications",
        headers=login["headers"],
    ).json()
    kinds = {x["kind"] for x in notes}
    assert "driver_assigned" in kinds
    assert "order_picked_up" in kinds
    assert "order_delivered" in kinds

    with SessionLocal() as db:
        tx = db.scalar(
            select(LoyaltyTransactionEntity).where(
                LoyaltyTransactionEntity.source_order_id == UUID(order["id"])
            )
        )
        assert tx is not None
        assert tx.transaction_type == "earn_order"
        assert tx.points > 0


def test_loyalty_accounts_are_isolated(client):
    a = login_phone(client, "01070000201")
    b = login_phone(client, "01070000202")

    a_account = client.get(
        "/api/v1/customer/loyalty",
        headers=a["headers"],
    )
    b_account = client.get(
        "/api/v1/customer/loyalty",
        headers=b["headers"],
    )

    assert a_account.status_code == 200
    assert b_account.status_code == 200
    assert a_account.json()["customer_id"] != b_account.json()["customer_id"]
    assert a_account.json()["balance_points"] == 0
    assert b_account.json()["balance_points"] == 0


def test_retention_summary_combines_core_retention_signals(login):
    client = login["client"]
    client.put(
        f"/api/v1/customer/favorites/chefs/{CHEF_ID}",
        headers=login["headers"],
    )

    summary = client.get(
        "/api/v1/customer/retention/summary",
        headers=login["headers"],
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["favorites"]["chefs_count"] == 1
    assert body["loyalty"]["balance_points"] == 0
    assert "unread_count" in body["notifications"]


def test_public_favorites_reject_unknown_targets(login):
    client = login["client"]

    chef = client.put(
        "/api/v1/customer/favorites/chefs/ffffffff-ffff-ffff-ffff-ffffffffffff",
        headers=login["headers"],
    )
    dish = client.put(
        "/api/v1/customer/favorites/dishes/ffffffff-ffff-ffff-ffff-ffffffffffff",
        headers=login["headers"],
    )

    assert chef.status_code == 404
    assert dish.status_code == 404


def test_support_public_reply_emits_notification(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "other",
            "subject": "استفسار عن النقاط",
            "description": "عايز أعرف النقاط بتتحسب إزاي.",
        },
    ).json()

    # Use seedless direct admin helper from previous tests is not accessible here,
    # so create/login a user and elevate role in DB for this isolated test.
    admin = login_phone(client, "01079999999")
    with SessionLocal() as db:
        from app.core.db_models import UserEntity
        user = db.get(UserEntity, UUID(admin["body"]["user"]["id"]))
        user.role = "admin"
        db.commit()

    # Re-login to receive an admin-role JWT.
    admin = login_phone(client, "01079999999")

    response = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers=admin["headers"],
        json={
            "body": "النقاط بتتحسب تلقائي بعد اكتمال التوصيل.",
            "is_internal": False,
        },
    )
    assert response.status_code == 200

    notes = client.get(
        "/api/v1/customer/notifications",
        headers=login["headers"],
    ).json()
    assert "support_reply" in {x["kind"] for x in notes}


def test_internal_support_note_does_not_notify_customer(login):
    client = login["client"]
    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "other",
            "subject": "استفسار داخلي",
            "description": "اختبار إشعار.",
        },
    ).json()

    admin = login_phone(client, "01078888888")
    with SessionLocal() as db:
        from app.core.db_models import UserEntity
        user = db.get(UserEntity, UUID(admin["body"]["user"]["id"]))
        user.role = "admin"
        db.commit()
    admin = login_phone(client, "01078888888")

    client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers=admin["headers"],
        json={
            "body": "ملاحظة داخلية فقط",
            "is_internal": True,
        },
    )

    notes = client.get(
        "/api/v1/customer/notifications",
        headers=login["headers"],
    ).json()
    assert "support_reply" not in {x["kind"] for x in notes}
