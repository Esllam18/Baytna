import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    ChefOrderFulfillmentEntity,
    OrderEntity,
    PaymentEntity,
    SpecialOrderRequestEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.payments.security import sign_webhook


CHEF_ID = "10000000-0000-0000-0000-000000000001"
CHEF_PHONE = "+201000000001"
OTHER_CHEF_PHONE = "+201000000002"


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
            phone=f"+20108{uuid4().int % 100000000:08d}",
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


def configure_schedule(client, chef_phone=CHEF_PHONE, *, capacity=5):
    chef = login_phone(client, chef_phone)
    days = [
        {
            "weekday": day,
            "is_available": True,
            "delivery_window_start": "12:00",
            "delivery_window_end": "18:00",
            "max_special_orders": capacity,
        }
        for day in range(7)
    ]
    response = client.put(
        "/api/v1/chef/schedule/weekly",
        headers=chef["headers"],
        json={"days": days},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 7
    return chef


def first_special_dish(client, chef_id=CHEF_ID):
    dishes = client.get(f"/api/v1/chefs/{chef_id}/signature-menu")
    assert dishes.status_code == 200
    return next(x for x in dishes.json() if x["is_special_order_available"])


def create_special(
    client,
    customer,
    service_date,
    *,
    request_type="special",
    quantity=2,
):
    dish = first_special_dish(client)
    response = client.post(
        "/api/v1/customer/special-orders",
        headers=customer["headers"],
        json={
            "dish_id": dish["id"],
            "request_type": request_type,
            "quantity": quantity,
            "requested_service_date": service_date.isoformat(),
            "requested_window_start": "13:00",
            "requested_window_end": "15:00",
            "customer_note": "بدون فلفل زيادة",
        },
    )
    assert response.status_code == 201, response.text
    return dish, response.json()


def accept_special(client, chef, special_id, *, unit_price_minor=None):
    payload = {
        "delivery_window_start": "13:00",
        "delivery_window_end": "15:00",
        "chef_note": "تمام هنجهزه",
    }
    if unit_price_minor is not None:
        payload["unit_price_minor"] = unit_price_minor
    response = client.post(
        f"/api/v1/chef/special-orders/{special_id}/accept",
        headers=chef["headers"],
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def checkout_special(client, customer, special_id, key):
    response = client.post(
        f"/api/v1/customer/special-orders/{special_id}/checkout",
        headers=customer["headers"],
        json={"idempotency_key": key},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_chef_can_publish_weekly_schedule(client):
    chef = configure_schedule(client)
    response = client.get(
        "/api/v1/chef/schedule/weekly",
        headers=chef["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 7
    assert {x["weekday"] for x in response.json()} == set(range(7))


def test_public_availability_uses_weekly_schedule(client):
    configure_schedule(client, capacity=3)
    start = date.today() + timedelta(days=3)
    response = client.get(
        f"/api/v1/chefs/{CHEF_ID}/availability",
        params={"start_date": start.isoformat(), "days": 3},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert all(x["source"] == "weekly" for x in response.json())
    assert all(x["capacity_total"] == 3 for x in response.json())


def test_date_override_can_close_a_day(client):
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=5)
    override = client.put(
        f"/api/v1/chef/schedule/overrides/{target.isoformat()}",
        headers=chef["headers"],
        json={"is_available": False, "reason": "إجازة"},
    )
    assert override.status_code == 200

    availability = client.get(
        f"/api/v1/chefs/{CHEF_ID}/availability",
        params={"start_date": target.isoformat(), "days": 1},
    )
    assert availability.status_code == 200
    assert availability.json()[0]["source"] == "override"
    assert availability.json()[0]["is_available"] is False


def test_special_order_requires_published_available_schedule(login):
    client = login["client"]
    dish = first_special_dish(client)
    target = date.today() + timedelta(days=3)
    response = client.post(
        "/api/v1/customer/special-orders",
        headers=login["headers"],
        json={
            "dish_id": dish["id"],
            "quantity": 1,
            "requested_service_date": target.isoformat(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "chef_not_available_for_date"


def test_customer_creates_special_order_for_signature_dish(login):
    client = login["client"]
    configure_schedule(client)
    target = date.today() + timedelta(days=3)
    dish, special = create_special(client, login, target)
    assert special["status"] == "chef_review"
    assert special["request_type"] == "special"
    assert special["dish_id"] == dish["id"]
    assert special["chef_id"] == CHEF_ID
    assert special["quantity"] == 2
    assert special["events"][0]["to_status"] == "chef_review"
    assert "phone" not in json.dumps(special).lower()


def test_preorder_type_is_supported(login):
    client = login["client"]
    configure_schedule(client)
    target = date.today() + timedelta(days=4)
    _, special = create_special(client, login, target, request_type="preorder")
    assert special["request_type"] == "preorder"


def test_prep_notice_is_enforced(login):
    client = login["client"]
    configure_schedule(client)
    dish = first_special_dish(client)
    response = client.post(
        "/api/v1/customer/special-orders",
        headers=login["headers"],
        json={
            "dish_id": dish["id"],
            "quantity": 1,
            "requested_service_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "special_order_prep_notice"


def test_capacity_limit_blocks_additional_requests(client):
    configure_schedule(client, capacity=1)
    target = date.today() + timedelta(days=4)
    a = login_phone(client, "01066000001")
    b = login_phone(client, "01066000002")
    create_special(client, a, target)
    dish = first_special_dish(client)
    blocked = client.post(
        "/api/v1/customer/special-orders",
        headers=b["headers"],
        json={
            "dish_id": dish["id"],
            "quantity": 1,
            "requested_service_date": target.isoformat(),
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "chef_not_available_for_date"


def test_chef_accepts_direct_quote(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=5)
    dish, special = create_special(client, login, target)
    body = accept_special(
        client,
        chef,
        special["id"],
        unit_price_minor=dish["base_price_minor"] + 500,
    )
    assert body["status"] == "awaiting_payment"
    assert body["final_service_date"] == target.isoformat()
    assert body["final_total_minor"] == (
        dish["base_price_minor"] + 500
    ) * body["quantity"]
    assert body["offer_expires_at"] is not None


def test_chef_counter_offer_and_customer_accepts(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=5)
    new_date = target + timedelta(days=1)
    dish, special = create_special(client, login, target)
    counter = client.post(
        f"/api/v1/chef/special-orders/{special['id']}/counter-offer",
        headers=chef["headers"],
        json={
            "proposed_service_date": new_date.isoformat(),
            "proposed_unit_price_minor": dish["base_price_minor"] + 1000,
            "proposed_window_start": "14:00",
            "proposed_window_end": "16:00",
            "chef_note": "ينفع اليوم التالي",
        },
    )
    assert counter.status_code == 200
    assert counter.json()["status"] == "counter_offer"

    accepted = client.post(
        f"/api/v1/customer/special-orders/{special['id']}/accept-counter-offer",
        headers=login["headers"],
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "awaiting_payment"
    assert body["final_service_date"] == new_date.isoformat()
    assert body["final_unit_price_minor"] == dish["base_price_minor"] + 1000


def test_chef_can_reject_request(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=5)
    _, special = create_special(client, login, target)
    response = client.post(
        f"/api/v1/chef/special-orders/{special['id']}/reject",
        headers=chef["headers"],
        json={"reason": "الكمية المطلوبة غير متاحة"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["rejection_reason"] == "الكمية المطلوبة غير متاحة"


def test_other_chef_cannot_operate_special_order(login):
    client = login["client"]
    configure_schedule(client)
    other = configure_schedule(client, OTHER_CHEF_PHONE)
    target = date.today() + timedelta(days=5)
    _, special = create_special(client, login, target)
    response = client.post(
        f"/api/v1/chef/special-orders/{special['id']}/accept",
        headers=other["headers"],
        json={},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "special_order_not_found"


def test_special_checkout_creates_order_without_daily_menu_item(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=5)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])
    body = checkout_special(client, login, special["id"], "special-checkout-0001")

    assert body["order"]["order_type"] == "special"
    assert body["order"]["status"] == "pending_payment"
    assert body["order"]["items"][0]["daily_menu_item_id"] is None
    assert body["payment"]["status"] == "pending"

    with SessionLocal() as db:
        order = db.get(OrderEntity, UUID(body["order"]["id"]))
        assert order.source_cart_id is None
        assert order.order_type == "special"


def test_special_checkout_is_idempotent(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=6)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])

    first = checkout_special(
        client,
        login,
        special["id"],
        "special-checkout-idempotent-001",
    )
    second = checkout_special(
        client,
        login,
        special["id"],
        "special-checkout-idempotent-001",
    )
    assert first["order"]["id"] == second["order"]["id"]
    assert first["payment"]["id"] == second["payment"]["id"]


def test_special_payment_success_schedules_and_preaccepts_fulfillment(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=6)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])
    checkout = checkout_special(
        client,
        login,
        special["id"],
        "special-payment-success-001",
    )

    payment = checkout["payment"]
    success = webhook(
        client,
        {
            "event_id": "evt-special-success-001",
            "event_type": "payment.succeeded",
            "payment_reference": payment["provider_reference"],
            "amount_minor": payment["amount_minor"],
            "currency": "EGP",
        },
    )
    assert success.status_code == 200, success.text

    detail = client.get(
        f"/api/v1/customer/special-orders/{special['id']}",
        headers=login["headers"],
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "scheduled"
    assert detail.json()["scheduled_at"] is not None

    order = client.get(
        f"/api/v1/customer/orders/{checkout['order']['id']}",
        headers=login["headers"],
    )
    assert order.status_code == 200
    assert order.json()["status"] == "accepted_by_chef"

    tracking = client.get(
        f"/api/v1/customer/orders/{checkout['order']['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.status_code == 200
    assert tracking.json()["display_status"] == "تم جدولة طلبك الخاص"

    with SessionLocal() as db:
        fulfillment = db.get(
            ChefOrderFulfillmentEntity,
            UUID(checkout["order"]["id"]),
        )
        assert fulfillment is not None
        assert fulfillment.stage == "accepted"


def test_failed_special_payment_does_not_cancel_quote(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=7)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])
    checkout = checkout_special(
        client,
        login,
        special["id"],
        "special-payment-fail-001",
    )

    payment = checkout["payment"]
    failed = webhook(
        client,
        {
            "event_id": "evt-special-fail-001",
            "event_type": "payment.failed",
            "payment_reference": payment["provider_reference"],
            "amount_minor": payment["amount_minor"],
            "currency": "EGP",
        },
    )
    assert failed.status_code == 200

    detail = client.get(
        f"/api/v1/customer/special-orders/{special['id']}",
        headers=login["headers"],
    )
    assert detail.json()["status"] == "awaiting_payment"

    with SessionLocal() as db:
        order = db.get(OrderEntity, UUID(checkout["order"]["id"]))
        assert order.status == "pending_payment"


def test_customer_can_cancel_before_special_payment(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=7)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])
    cancelled = client.post(
        f"/api/v1/customer/special-orders/{special['id']}/cancel",
        headers=login["headers"],
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_special_order_customer_ownership_is_enforced(client):
    configure_schedule(client)
    a = login_phone(client, "01066110001")
    b = login_phone(client, "01066110002")
    target = date.today() + timedelta(days=5)
    _, special = create_special(client, a, target)
    detail = client.get(
        f"/api/v1/customer/special-orders/{special['id']}",
        headers=b["headers"],
    )
    assert detail.status_code == 404


def test_admin_can_list_special_orders(login):
    client = login["client"]
    configure_schedule(client)
    target = date.today() + timedelta(days=5)
    _, special = create_special(client, login, target)
    response = client.get(
        "/api/v1/admin/special-orders",
        headers=create_admin_headers(),
    )
    assert response.status_code == 200
    assert special["id"] in {x["id"] for x in response.json()}


def test_scheduled_special_order_can_start_preparing_without_second_accept(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=8)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])
    checkout = checkout_special(
        client,
        login,
        special["id"],
        "special-prep-direct-001",
    )
    payment = checkout["payment"]
    result = webhook(
        client,
        {
            "event_id": "evt-special-prep-direct-001",
            "event_type": "payment.succeeded",
            "payment_reference": payment["provider_reference"],
            "amount_minor": payment["amount_minor"],
            "currency": "EGP",
        },
    )
    assert result.status_code == 200

    preparing = client.post(
        f"/api/v1/chef/orders/{checkout['order']['id']}/start-preparing",
        headers=chef["headers"],
        json={"chef_note": "بدأنا تجهيز الطلب الخاص"},
    )
    assert preparing.status_code == 200, preparing.text
    assert preparing.json()["order_status"] == "preparing"
    assert preparing.json()["fulfillment_stage"] == "preparing"


def test_expired_offer_blocks_checkout(login):
    client = login["client"]
    chef = configure_schedule(client)
    target = date.today() + timedelta(days=8)
    _, special = create_special(client, login, target)
    accept_special(client, chef, special["id"])

    with SessionLocal() as db:
        row = db.get(SpecialOrderRequestEntity, UUID(special["id"]))
        from app.core.security import utc_now
        row.offer_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    response = client.post(
        f"/api/v1/customer/special-orders/{special['id']}/checkout",
        headers=login["headers"],
        json={"idempotency_key": "special-expired-offer-001"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "special_order_not_awaiting_payment"

    detail = client.get(
        f"/api/v1/customer/special-orders/{special['id']}",
        headers=login["headers"],
    )
    assert detail.json()["status"] == "expired"
