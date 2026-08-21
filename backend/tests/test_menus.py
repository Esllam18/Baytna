from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.db_models import ChefProfileEntity, DishEntity


CHEF_1_PHONE = "+201000000001"
CHEF_1_ID = "10000000-0000-0000-0000-000000000001"
CHEF_2_ID = "10000000-0000-0000-0000-000000000002"


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


def test_public_signature_menu_returns_active_dishes(client):
    response = client.get(f"/api/v1/chefs/{CHEF_1_ID}/signature-menu")
    assert response.status_code == 200
    names = {x["name"] for x in response.json()}
    assert "محشي مشكل" in names
    assert "طاجن بامية باللحمة" in names


def test_customer_cannot_use_chef_menu_endpoints(login):
    response = login["client"].post(
        "/api/v1/chef/signature-menu",
        headers=login["headers"],
        json={
            "name": "طبق غير مسموح",
            "base_price_minor": 10000,
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_chef_can_create_and_update_signature_dish(client):
    chef = login_phone(client, CHEF_1_PHONE)

    created = client.post(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
        json={
            "name": "كفتة بالبطاطس",
            "description": "صينية كفتة وبطاطس.",
            "category": "صواني",
            "base_price_minor": 19500,
            "prep_notice_hours": 24,
            "is_special_order_available": True,
        },
    )
    assert created.status_code == 201
    dish = created.json()
    assert dish["chef_id"] == CHEF_1_ID
    assert dish["is_active"] is True

    updated = client.patch(
        f"/api/v1/chef/signature-menu/{dish['id']}",
        headers=chef["headers"],
        json={
            "base_price_minor": 20500,
            "is_special_order_available": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["base_price_minor"] == 20500
    assert updated.json()["is_special_order_available"] is False


def test_open_kitchen_and_publish_today_menu(client):
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=1)).isoformat()

    opened = client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "delivery_window_start": "13:00",
            "delivery_window_end": "17:00",
        },
    )
    assert opened.status_code == 200
    assert opened.json()["status"] == "open"

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
                    "quantity_total": 7,
                    "max_per_order": 3,
                }
            ],
        },
    )
    assert published.status_code == 200
    body = published.json()
    assert body["kitchen_status"] == "open"
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity_available"] == 7
    assert body["items"][0]["availability_label"] == "متاح اليوم"

    public = client.get(
        f"/api/v1/chefs/{CHEF_1_ID}/today-menu",
        params={"date": service_date},
    )
    assert public.status_code == 200
    assert len(public.json()["items"]) == 1


def test_chef_cannot_publish_another_chefs_dish(client):
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=2)).isoformat()

    client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )

    other_menu = client.get(
        f"/api/v1/chefs/{CHEF_2_ID}/signature-menu"
    )
    other_dish_id = other_menu.json()[0]["id"]

    response = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {
                    "dish_id": other_dish_id,
                    "quantity_total": 3,
                }
            ],
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dish_not_found"


def test_zero_quantity_becomes_sold_out(client):
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=3)).isoformat()

    client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )

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
                    "quantity_total": 5,
                }
            ],
        },
    )
    item_id = published.json()["items"][0]["id"]

    sold_out = client.patch(
        f"/api/v1/chef/today-menu/{item_id}/quantity",
        headers=chef["headers"],
        json={"quantity_available": 0},
    )
    assert sold_out.status_code == 200
    assert sold_out.json()["status"] == "sold_out"
    assert sold_out.json()["availability_label"] == "نفدت الكمية اليوم"


def test_available_quantity_cannot_exceed_original_total(client):
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=4)).isoformat()

    client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
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
            "items": [{"dish_id": dish_id, "quantity_total": 5}],
        },
    )
    item_id = published.json()["items"][0]["id"]

    response = client.patch(
        f"/api/v1/chef/today-menu/{item_id}/quantity",
        headers=chef["headers"],
        json={"quantity_available": 6},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "quantity_exceeds_total"


def test_closed_kitchen_is_hidden_from_public(client):
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=5)).isoformat()

    client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    )
    dish_id = signature.json()[0]["id"]

    client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [{"dish_id": dish_id, "quantity_total": 2}],
        },
    )

    closed = client.post(
        f"/api/v1/chef/workdays/{service_date}/close",
        headers=chef["headers"],
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    public = client.get(
        f"/api/v1/chefs/{CHEF_1_ID}/today-menu",
        params={"date": service_date},
    )
    assert public.status_code == 200
    assert public.json()["kitchen_status"] == "closed"
    assert public.json()["items"] == []


def test_deactivated_signature_dish_disappears_publicly(client):
    chef = login_phone(client, CHEF_1_PHONE)
    owner = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    )
    dish_id = owner.json()[0]["id"]

    response = client.patch(
        f"/api/v1/chef/signature-menu/{dish_id}",
        headers=chef["headers"],
        json={"is_active": False},
    )
    assert response.status_code == 200

    public = client.get(f"/api/v1/chefs/{CHEF_1_ID}/signature-menu")
    public_ids = {x["id"] for x in public.json()}
    assert dish_id not in public_ids

    owner_all = client.get(
        "/api/v1/chef/signature-menu",
        params={"include_inactive": "true"},
        headers=chef["headers"],
    )
    owner_ids = {x["id"] for x in owner_all.json()}
    assert dish_id in owner_ids


def test_dashboard_summarizes_today_menu(client):
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=6)).isoformat()

    client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    ).json()

    client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {"dish_id": signature[0]["id"], "quantity_total": 4},
                {"dish_id": signature[1]["id"], "quantity_total": 0},
            ],
        },
    )

    dashboard = client.get(
        "/api/v1/chef/dashboard",
        params={"date": service_date},
        headers=chef["headers"],
    )
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["kitchen_status"] == "open"
    assert body["today_items"] == 2
    assert body["sold_out_items"] == 1
    assert body["total_quantity"] == 4
    assert body["available_quantity"] == 4
