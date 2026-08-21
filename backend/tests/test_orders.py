from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.db_models import (
    ChefWorkdayEntity,
    DailyMenuItemEntity,
    InventoryReservationEntity,
    OrderEntity,
)
from app.core.security import utc_now
from app.modules.orders.service import OrderService
from app.core.config import get_settings


CHEF_1_ID = "10000000-0000-0000-0000-000000000001"
CHEF_2_ID = "10000000-0000-0000-0000-000000000002"
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


def publish_today_item(client, chef_id: str, chef_phone: str, service_date: str, quantity=10):
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
                    "max_per_order": 5,
                }
            ],
        },
    )
    assert published.status_code == 200
    return published.json()["items"][0]


def test_cart_is_created_lazily(login):
    response = login["client"].get(
        "/api/v1/customer/cart",
        headers=login["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["items"] == []
    assert body["chef_id"] is None


def test_add_today_item_to_cart(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=1)).isoformat()
    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=10,
    )

    response = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 2,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["chef_id"] == CHEF_1_ID
    assert body["service_date"] == service_date
    assert body["items"][0]["quantity"] == 2
    assert body["subtotal_minor"] > 0


def test_cart_rejects_multiple_chefs(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=2)).isoformat()

    first = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=10,
    )

    second = publish_today_item(
        client,
        CHEF_2_ID,
        "+201000000002",
        service_date,
        quantity=10,
    )

    add_first = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": first["id"], "quantity": 1},
    )
    assert add_first.status_code == 201

    add_second = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": second["id"], "quantity": 1},
    )
    assert add_second.status_code == 409
    assert (
        add_second.json()["error"]["code"]
        == "cart_multiple_chefs_not_allowed"
    )


def test_cart_enforces_max_per_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=3)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=10,
    )

    response = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 6,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "quantity_above_max_per_order"


def test_cart_rejects_more_than_available(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=4)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=3,
    )

    response = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 4,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_inventory"


def test_create_order_reserves_inventory_and_converts_cart(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=5)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=8,
    )

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 3,
        },
    ).json()

    created = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    )
    assert created.status_code == 201
    order = created.json()
    assert order["status"] == "pending_payment"
    assert order["chef_id"] == CHEF_1_ID
    assert order["service_date"] == service_date
    assert order["items"][0]["quantity"] == 3
    assert order["inventory_hold_expires_at"] is not None
    assert order["timeline"][0]["to_status"] == "pending_payment"

    with SessionLocal() as db:
        db_item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert db_item.quantity_available == 5

        reservation = db.scalar(
            select(InventoryReservationEntity).where(
                InventoryReservationEntity.order_id == UUID(order["id"])
            )
        )
        assert reservation is not None
        assert reservation.status == "active"
        assert reservation.quantity == 3


def test_pending_order_cancellation_releases_inventory(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=6)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=5,
    )
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 2},
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    cancelled = client.post(
        f"/api/v1/customer/orders/{order['id']}/cancel",
        headers=login["headers"],
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["inventory_hold_expires_at"] is None
    assert cancelled.json()["timeline"][-1]["to_status"] == "cancelled"

    with SessionLocal() as db:
        db_item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert db_item.quantity_available == 5


def test_second_checkout_cannot_oversell_same_item(client):
    customer_a = login_phone(client, "01077770001")
    customer_b = login_phone(client, "01077770002")
    service_date = (date.today() + timedelta(days=7)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=3,
    )

    cart_a = client.post(
        "/api/v1/customer/cart/items",
        headers=customer_a["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 2},
    ).json()

    cart_b = client.post(
        "/api/v1/customer/cart/items",
        headers=customer_b["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 2},
    ).json()

    first = client.post(
        "/api/v1/customer/orders",
        headers=customer_a["headers"],
        json={"cart_id": cart_a["id"]},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/customer/orders",
        headers=customer_b["headers"],
        json={"cart_id": cart_b["id"]},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] in {
        "insufficient_inventory",
        "inventory_changed",
    }

    with SessionLocal() as db:
        db_item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert db_item.quantity_available == 1


def test_expired_hold_releases_inventory_and_expires_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=8)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=4,
    )
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 3},
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    with SessionLocal() as db:
        reservation = db.scalar(
            select(InventoryReservationEntity).where(
                InventoryReservationEntity.order_id == UUID(order["id"])
            )
        )
        reservation.expires_at = utc_now() - timedelta(seconds=1)

        db_order = db.get(OrderEntity, UUID(order["id"]))
        db_order.inventory_hold_expires_at = reservation.expires_at
        db.commit()

    # Any order read performs housekeeping.
    detail = client.get(
        f"/api/v1/customer/orders/{order['id']}",
        headers=login["headers"],
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "expired"
    assert detail.json()["timeline"][-1]["to_status"] == "expired"

    with SessionLocal() as db:
        db_item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert db_item.quantity_available == 4


def test_sold_out_item_becomes_available_after_release(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=9)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=2,
    )
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 2},
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    with SessionLocal() as db:
        item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert item.quantity_available == 0
        assert item.status == "sold_out"

    client.post(
        f"/api/v1/customer/orders/{order['id']}/cancel",
        headers=login["headers"],
    )

    with SessionLocal() as db:
        item = db.get(DailyMenuItemEntity, UUID(menu_item["id"]))
        assert item.quantity_available == 2
        assert item.status == "available"


def test_customer_cannot_read_another_customers_order(client):
    customer_a = login_phone(client, "01077771111")
    customer_b = login_phone(client, "01077772222")
    service_date = (date.today() + timedelta(days=10)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=3,
    )

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer_a["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 1},
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=customer_a["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    forbidden = client.get(
        f"/api/v1/customer/orders/{order['id']}",
        headers=customer_b["headers"],
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "order_not_found"


def test_order_list_contains_created_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=11)).isoformat()

    menu_item = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=3,
    )
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 1},
    ).json()
    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    listing = client.get(
        "/api/v1/customer/orders",
        headers=login["headers"],
    )
    assert listing.status_code == 200
    ids = {x["id"] for x in listing.json()}
    assert order["id"] in ids
