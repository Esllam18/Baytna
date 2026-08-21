import json
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    DeliveryTaskEntity,
    DriverProfileEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
)
from app.modules.payments.security import sign_webhook


CHEF_PHONE = "+201000000001"
DRIVER_1_PHONE = "+201090000001"
DRIVER_2_PHONE = "+201090000002"


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


def create_address(client, customer, area="6 أكتوبر"):
    response = client.post(
        "/api/v1/customer/addresses",
        headers=customer["headers"],
        json={
            "label": "المنزل",
            "area": area,
            "street": "شارع التحرير",
            "building": "12",
            "floor": "3",
            "apartment": "7",
            "latitude": "29.9701000",
            "longitude": "30.9438000",
            "is_default": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def publish_today_item(client, service_date: str, quantity=10):
    chef = login_phone(client, CHEF_PHONE)

    opened = client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    assert opened.status_code == 200

    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    ).json()

    published = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {
                    "dish_id": signature[0]["id"],
                    "quantity_total": quantity,
                    "max_per_order": 10,
                }
            ],
        },
    )
    assert published.status_code == 200
    return published.json()["items"][0]


def create_ready_order(
    client,
    customer,
    service_date: str,
    *,
    create_customer_address=True,
):
    if create_customer_address:
        create_address(client, customer)

    menu_item = publish_today_item(client, service_date, quantity=10)

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 2,
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
        json={"idempotency_key": f"delivery-pay-{order['id']}"},
    ).json()

    success = webhook(
        client,
        {
            "event_id": f"delivery-pay-success-{order['id']}",
            "event_type": "payment.succeeded",
            "payment_reference": intent["provider_reference"],
            "amount_minor": intent["amount_minor"],
            "currency": "EGP",
        },
    )
    assert success.status_code == 200

    chef = login_phone(client, CHEF_PHONE)
    assert client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={},
    ).status_code == 200
    assert client.post(
        f"/api/v1/chef/orders/{order['id']}/start-preparing",
        headers=chef["headers"],
        json={},
    ).status_code == 200
    ready = client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={},
    )
    assert ready.status_code == 200

    return menu_item, order


def make_driver_available(client, phone=DRIVER_1_PHONE):
    driver = login_phone(client, phone)
    response = client.put(
        "/api/v1/driver/availability",
        headers=driver["headers"],
        json={"available": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "available"
    return driver


def test_customer_address_is_snapshotted_into_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=60)).isoformat()
    create_address(client, login, area="الحي السابع")

    menu_item = publish_today_item(client, service_date)
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 1},
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    )
    assert order.status_code == 201

    with SessionLocal() as db:
        snapshot = db.get(OrderDeliveryAddressEntity, UUID(order.json()["id"]))
        assert snapshot is not None
        assert snapshot.area == "الحي السابع"
        assert snapshot.street == "شارع التحرير"


def test_driver_must_be_available_to_see_missions(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=61)).isoformat()
    create_ready_order(client, login, service_date)

    driver = login_phone(client, DRIVER_1_PHONE)
    response = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "driver_not_available"


def test_ready_order_appears_as_available_delivery_mission(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=62)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

    missions = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    )
    assert missions.status_code == 200
    ids = {x["order_id"] for x in missions.json()}
    assert order["id"] in ids

    mission = next(x for x in missions.json() if x["order_id"] == order["id"])
    assert mission["status"] == "unassigned"
    assert mission["navigation_ready"] is True
    assert mission["dropoff"]["area"] == "6 أكتوبر"
    assert "phone" not in json.dumps(mission).lower()


def test_driver_accepts_mission_atomically(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=63)).isoformat()
    _, order = create_ready_order(client, login, service_date)

    driver1 = make_driver_available(client, DRIVER_1_PHONE)
    driver2 = make_driver_available(client, DRIVER_2_PHONE)

    missions = client.get(
        "/api/v1/driver/missions/available",
        headers=driver1["headers"],
    ).json()
    task = next(x for x in missions if x["order_id"] == order["id"])

    accepted = client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver1["headers"],
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "to_pickup"
    assert accepted.json()["order_status"] == "assigned_to_driver"

    second = client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver2["headers"],
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] in {
        "order_not_ready_for_driver",
        "mission_already_claimed",
    }


def test_driver_cannot_accept_two_active_missions(login):
    client = login["client"]
    d1 = (date.today() + timedelta(days=64)).isoformat()
    d2 = (date.today() + timedelta(days=65)).isoformat()

    _, order1 = create_ready_order(client, login, d1)

    # New customer avoids one-date cart/order conflicts.
    customer2 = login_phone(client, "01088880002")
    _, order2 = create_ready_order(client, customer2, d2)

    driver = make_driver_available(client)
    missions = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    ).json()

    task1 = next(x for x in missions if x["order_id"] == order1["id"])
    task2 = next(x for x in missions if x["order_id"] == order2["id"])

    first = client.post(
        f"/api/v1/driver/missions/{task1['id']}/accept",
        headers=driver["headers"],
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/driver/missions/{task2['id']}/accept",
        headers=driver["headers"],
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] in {
        "driver_not_available",
        "driver_has_active_mission",
    }


def test_missing_delivery_address_blocks_mission_acceptance(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=66)).isoformat()
    _, order = create_ready_order(
        client,
        login,
        service_date,
        create_customer_address=False,
    )
    driver = make_driver_available(client)

    missions = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    ).json()
    task = next(x for x in missions if x["order_id"] == order["id"])
    assert task["navigation_ready"] is False

    response = client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver["headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "delivery_address_missing"


def test_full_driver_delivery_workflow_and_tracking(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=67)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

    task = next(
        x
        for x in client.get(
            "/api/v1/driver/missions/available",
            headers=driver["headers"],
        ).json()
        if x["order_id"] == order["id"]
    )

    accepted = client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver["headers"],
    )
    assert accepted.status_code == 200

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "المندوب في طريقه للشيف"

    arrived = client.post(
        f"/api/v1/driver/missions/{task['id']}/arrive-pickup",
        headers=driver["headers"],
    )
    assert arrived.status_code == 200
    assert arrived.json()["status"] == "at_pickup"

    picked = client.post(
        f"/api/v1/driver/missions/{task['id']}/confirm-pickup",
        headers=driver["headers"],
    )
    assert picked.status_code == 200
    assert picked.json()["status"] == "picked_up"
    assert picked.json()["order_status"] == "picked_up"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "المندوب استلم الطلب"

    route = client.post(
        f"/api/v1/driver/missions/{task['id']}/start-delivery",
        headers=driver["headers"],
    )
    assert route.status_code == 200
    assert route.json()["status"] == "to_customer"
    assert route.json()["order_status"] == "out_for_delivery"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "طلبك في الطريق"

    delivered = client.post(
        f"/api/v1/driver/missions/{task['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "otp",
            "proof_reference": "OTP-4821",
        },
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert delivered.json()["order_status"] == "delivered"
    assert delivered.json()["delivery_proof_type"] == "otp"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "تم توصيل طلبك"
    assert tracking.json()["delivered_at"] is not None

    status = client.get(
        "/api/v1/driver/status",
        headers=driver["headers"],
    )
    assert status.json()["status"] == "available"
    assert status.json()["active_mission_id"] is None


def test_proof_of_delivery_is_required(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=68)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

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

    response = client.post(
        f"/api/v1/driver/missions/{task['id']}/deliver",
        headers=driver["headers"],
        json={"proof_type": "otp", "proof_reference": "x"},
    )
    assert response.status_code == 422


def test_delivery_issue_can_pause_and_resume(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=69)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

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

    issue = client.post(
        f"/api/v1/driver/missions/{task['id']}/issue",
        headers=driver["headers"],
        json={
            "issue_code": "customer_unreachable",
            "note": "حاولت التواصل عبر الدعم ولم يتم الرد.",
        },
    )
    assert issue.status_code == 200
    assert issue.json()["status"] == "delivery_issue"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert tracking.json()["display_status"] == "يوجد تحديث في التوصيل"

    resumed = client.post(
        f"/api/v1/driver/missions/{task['id']}/resume",
        headers=driver["headers"],
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "to_customer"
    assert resumed.json()["issue_code"] is None


def test_other_driver_cannot_operate_assigned_mission(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=70)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver1 = make_driver_available(client, DRIVER_1_PHONE)
    driver2 = make_driver_available(client, DRIVER_2_PHONE)

    task = next(
        x
        for x in client.get(
            "/api/v1/driver/missions/available",
            headers=driver1["headers"],
        ).json()
        if x["order_id"] == order["id"]
    )

    client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver1["headers"],
    )

    response = client.post(
        f"/api/v1/driver/missions/{task['id']}/arrive-pickup",
        headers=driver2["headers"],
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "mission_not_found"


def test_completed_mission_appears_in_history(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=71)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

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
    client.post(
        f"/api/v1/driver/missions/{task['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "photo",
            "proof_reference": "proof://delivery/image-001",
        },
    )

    history = client.get(
        "/api/v1/driver/missions/history",
        headers=driver["headers"],
    )
    assert history.status_code == 200
    ids = {x["id"] for x in history.json()}
    assert task["id"] in ids


def test_customer_cannot_use_driver_endpoints(login):
    response = login["client"].get(
        "/api/v1/driver/status",
        headers=login["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
