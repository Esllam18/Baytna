from datetime import date, timedelta

from tests.test_fulfillment import (
    CHEF_1_PHONE,
    create_confirmed_order,
    login_phone,
)
from tests.test_special_orders import (
    configure_schedule,
    create_special,
)


def test_chef_self_profile_contract(login):
    client = login["client"]
    chef = login_phone(client, CHEF_1_PHONE)

    response = client.get(
        "/api/v1/chef/profile",
        headers=chef["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "10000000-0000-0000-0000-000000000001"
    assert body["display_name"]
    assert body["status"] == "active"
    assert body["is_verified"] is True
    assert set(body) == {
        "id",
        "display_name",
        "specialty",
        "area",
        "status",
        "rating",
        "is_verified",
        "is_open_today",
    }


def test_customer_cannot_use_chef_app_endpoints(login):
    client = login["client"]

    profile = client.get(
        "/api/v1/chef/profile",
        headers=login["headers"],
    )
    dashboard = client.get(
        "/api/v1/chef/app-dashboard",
        headers=login["headers"],
    )

    assert profile.status_code == 403
    assert dashboard.status_code == 403


def test_chef_app_dashboard_menu_metrics(login):
    client = login["client"]
    chef = login_phone(client, CHEF_1_PHONE)
    service_date = (date.today() + timedelta(days=170)).isoformat()

    opened = client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    assert opened.status_code == 200

    dishes = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    ).json()
    dish = next(x for x in dishes if x["is_active"])

    menu = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {
                    "dish_id": dish["id"],
                    "quantity_total": 7,
                    "max_per_order": 3,
                }
            ],
        },
    )
    assert menu.status_code == 200

    response = client.get(
        f"/api/v1/chef/app-dashboard?date={service_date}",
        headers=chef["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kitchen_status"] == "open"
    assert body["today_items"] == 1
    assert body["available_quantity"] == 7
    assert body["signature_dishes"] >= 1


def test_chef_app_dashboard_counts_new_confirmed_order(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=171)).isoformat()

    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
    )
    chef = login_phone(client, CHEF_1_PHONE)

    response = client.get(
        f"/api/v1/chef/app-dashboard?date={service_date}",
        headers=chef["headers"],
    )
    assert response.status_code == 200
    assert response.json()["orders_new"] >= 1

    queue = client.get(
        "/api/v1/chef/orders?stage=new",
        headers=chef["headers"],
    )
    assert order["id"] in {x["order_id"] for x in queue.json()}


def test_chef_app_dashboard_counts_special_review(login):
    client = login["client"]
    chef = configure_schedule(client)
    service_date = date.today() + timedelta(days=45)

    _, special = create_special(
        client,
        login,
        service_date,
    )

    response = client.get(
        f"/api/v1/chef/app-dashboard?date={service_date.isoformat()}",
        headers=chef["headers"],
    )
    assert response.status_code == 200
    assert response.json()["special_review"] >= 1

    queue = client.get(
        "/api/v1/chef/special-orders?status=chef_review",
        headers=chef["headers"],
    )
    assert special["id"] in {x["id"] for x in queue.json()}


def test_chef_app_dashboard_shape(login):
    client = login["client"]
    chef = login_phone(client, CHEF_1_PHONE)

    response = client.get(
        "/api/v1/chef/app-dashboard",
        headers=chef["headers"],
    )
    assert response.status_code == 200
    assert set(response.json()) == {
        "chef",
        "service_date",
        "kitchen_status",
        "signature_dishes",
        "today_items",
        "sold_out_items",
        "available_quantity",
        "orders_new",
        "orders_accepted",
        "orders_preparing",
        "orders_packaging",
        "orders_ready",
        "special_review",
        "special_counter_offer",
        "special_awaiting_payment",
        "special_scheduled",
    }
