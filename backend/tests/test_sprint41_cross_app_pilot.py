from datetime import date, timedelta

from tests.test_admin_operations import admin_headers
from tests.test_delivery import (
    DRIVER_1_PHONE,
    create_address,
    login_phone as delivery_login,
    make_driver_available,
)
from tests.test_fulfillment import (
    CHEF_1_PHONE,
    create_confirmed_order,
)
from tests.test_post_order import review_payload


def test_universal_push_registration_supports_customer_chef_driver(login):
    client = login["client"]
    chef = delivery_login(client, CHEF_1_PHONE)
    driver = delivery_login(client, DRIVER_1_PHONE)

    actors = [
        (login["headers"], "customer-pilot-token-0000001", "customer"),
        (chef["headers"], "chef-pilot-token-00000000002", "chef"),
        (driver["headers"], "driver-pilot-token-000000003", "driver"),
    ]

    for headers, token, name in actors:
        created = client.post(
            "/api/v1/notifications/devices",
            headers=headers,
            json={
                "platform": "android",
                "token": token,
                "device_name": f"pilot-{name}",
                "app_version": "0.41.0",
            },
        )
        assert created.status_code == 201
        assert created.json()["platform"] == "android"
        assert created.json()["is_active"] is True

        devices = client.get(
            "/api/v1/notifications/devices",
            headers=headers,
        )
        assert devices.status_code == 200
        assert any(x["device_name"] == f"pilot-{name}" for x in devices.json())

        prefs = client.put(
            "/api/v1/notifications/preferences",
            headers=headers,
            json={
                "push_enabled": True,
                "sms_enabled": False,
                "order_updates": True,
                "support_updates": True,
                "marketing_enabled": False,
            },
        )
        assert prefs.status_code == 200
        assert prefs.json()["push_enabled"] is True


def test_cross_app_order_delivery_review_support_admin_journey(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=34)).isoformat()

    create_address(client, login)

    _, order, _ = create_confirmed_order(
        client,
        login,
        service_date=service_date,
        quantity=1,
        stock=8,
    )

    chef = delivery_login(client, CHEF_1_PHONE)

    accepted = client.post(
        f"/api/v1/chef/orders/{order['id']}/accept",
        headers=chef["headers"],
        json={"chef_note": "Pilot flow accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["fulfillment_stage"] == "accepted"

    preparing = client.post(
        f"/api/v1/chef/orders/{order['id']}/start-preparing",
        headers=chef["headers"],
        json={"chef_note": "Pilot cooking"},
    )
    assert preparing.status_code == 200
    assert preparing.json()["fulfillment_stage"] == "preparing"

    packaging = client.post(
        f"/api/v1/chef/orders/{order['id']}/start-packaging",
        headers=chef["headers"],
        json={"chef_note": "Pilot packaging"},
    )
    assert packaging.status_code == 200
    assert packaging.json()["fulfillment_stage"] == "packaging"

    ready = client.post(
        f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",
        headers=chef["headers"],
        json={"chef_note": "Pilot ready"},
    )
    assert ready.status_code == 200
    assert ready.json()["fulfillment_stage"] == "ready"

    driver = make_driver_available(client, DRIVER_1_PHONE)
    offers = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    )
    assert offers.status_code == 200
    mission = next(x for x in offers.json() if x["order_id"] == order["id"])

    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/accept",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/arrive-pickup",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/confirm-pickup",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{mission['id']}/start-delivery",
        headers=driver["headers"],
    ).status_code == 200

    delivered = client.post(
        f"/api/v1/driver/missions/{mission['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "otp",
            "proof_reference": "4182",
        },
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"

    tracking = client.get(
        f"/api/v1/customer/orders/{order['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.status_code == 200
    assert tracking.json()["status"] == "delivered"

    review = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(chef_overall=5, delivery_overall=5),
    )
    assert review.status_code == 201

    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "order_id": order["id"],
            "category": "other",
            "subject": "Pilot journey confirmation",
            "description": "Cross-app journey reached delivered state.",
            "priority": "normal",
            "attachment_ids": [],
        },
    )
    assert ticket.status_code == 201

    admin_auth, _ = admin_headers()
    admin_order = client.get(
        f"/api/v1/admin/orders/{order['id']}",
        headers=admin_auth,
    )
    assert admin_order.status_code == 200
    assert admin_order.json()["order"]["status"] == "delivered"
    assert any(
        x["id"] == ticket.json()["id"]
        for x in admin_order.json()["support_tickets"]
    )


def test_chef_can_upload_and_bind_public_dish_image(login):
    client = login["client"]
    chef = delivery_login(client, CHEF_1_PHONE)

    dishes = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    )
    assert dishes.status_code == 200
    dish_id = dishes.json()[0]["id"]

    raw = b"\xff\xd8\xff\xe0" + b"pilot-dish-image" * 30
    created = client.post(
        "/api/v1/media/uploads",
        headers=chef["headers"],
        json={
            "purpose": "dish_image",
            "visibility": "public",
            "filename": "pilot-dish.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": len(raw),
        },
    )
    assert created.status_code == 201
    upload = created.json()

    put = client.put(
        upload["upload_url"],
        content=raw,
        headers=upload["upload_headers"],
    )
    assert put.status_code == 200

    completed = client.post(
        f"/api/v1/media/{upload['asset']['id']}/complete",
        headers=chef["headers"],
    )
    assert completed.status_code == 200
    assert completed.json()["asset"]["status"] == "ready"

    bound = client.put(
        f"/api/v1/chef/signature-menu/{dish_id}/media",
        headers=chef["headers"],
        json={"media_asset_id": upload["asset"]["id"]},
    )
    assert bound.status_code == 200
    assert bound.json()["media_asset_id"] == upload["asset"]["id"]
    assert "/api/v1/media/public/" in bound.json()["image_url"]


def test_customer_support_ticket_accepts_ready_private_attachment(login):
    client = login["client"]
    raw = b"\x89PNG\r\n\x1a\n" + b"pilot-support-image" * 25

    created = client.post(
        "/api/v1/media/uploads",
        headers=login["headers"],
        json={
            "purpose": "support_attachment",
            "visibility": "private",
            "filename": "problem.png",
            "mime_type": "image/png",
            "size_bytes": len(raw),
        },
    )
    assert created.status_code == 201
    upload = created.json()

    assert client.put(
        upload["upload_url"],
        content=raw,
        headers=upload["upload_headers"],
    ).status_code == 200

    completed = client.post(
        f"/api/v1/media/{upload['asset']['id']}/complete",
        headers=login["headers"],
    )
    assert completed.status_code == 200

    ticket = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "category": "app_issue",
            "subject": "Pilot image attachment",
            "description": "Image attachment pipeline test.",
            "priority": "normal",
            "attachment_ids": [upload["asset"]["id"]],
        },
    )
    assert ticket.status_code == 201
    assert ticket.json()["messages"][0]["attachments"][0]["media_asset_id"] == upload["asset"]["id"]
