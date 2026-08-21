from datetime import date, timedelta

from tests.test_delivery import (
    DRIVER_1_PHONE,
    DRIVER_2_PHONE,
    create_ready_order,
    login_phone,
    make_driver_available,
)


def test_driver_self_profile_contract(login):
    client = login["client"]
    driver = login_phone(client, DRIVER_1_PHONE)

    response = client.get(
        "/api/v1/driver/profile",
        headers=driver["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == DRIVER_1_PHONE
    assert body["status"] == "offline"
    assert set(body) == {
        "id",
        "phone",
        "status",
        "rating",
    }


def test_customer_cannot_use_driver_app_aggregate(login):
    client = login["client"]

    assert client.get(
        "/api/v1/driver/profile",
        headers=login["headers"],
    ).status_code == 403

    assert client.get(
        "/api/v1/driver/app-dashboard",
        headers=login["headers"],
    ).status_code == 403


def test_driver_dashboard_offline_has_no_available_offers(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=55)).isoformat()
    create_ready_order(client, login, service_date)
    driver = login_phone(client, DRIVER_1_PHONE)

    response = client.get(
        "/api/v1/driver/app-dashboard",
        headers=driver["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["driver"]["status"] == "offline"
    assert body["active_mission"] is None
    assert body["available_missions_count"] == 0


def test_driver_dashboard_available_counts_ready_mission(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=56)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

    response = client.get(
        "/api/v1/driver/app-dashboard",
        headers=driver["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["driver"]["status"] == "available"
    assert body["available_missions_count"] >= 1
    assert body["active_mission"] is None

    offers = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    ).json()
    assert order["id"] in {x["order_id"] for x in offers}


def test_available_mission_preview_then_accept_becomes_active(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=57)).isoformat()
    _, order = create_ready_order(client, login, service_date)
    driver = make_driver_available(client)

    offers = client.get(
        "/api/v1/driver/missions/available",
        headers=driver["headers"],
    ).json()
    task = next(x for x in offers if x["order_id"] == order["id"])

    preview = client.get(
        f"/api/v1/driver/missions/available/{task['id']}",
        headers=driver["headers"],
    )
    assert preview.status_code == 200
    assert preview.json()["status"] == "unassigned"
    assert preview.json()["dropoff"]["area"] == "6 أكتوبر"
    assert "phone" not in preview.text.lower()

    accepted = client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver["headers"],
    )
    assert accepted.status_code == 200

    dashboard = client.get(
        "/api/v1/driver/app-dashboard",
        headers=driver["headers"],
    ).json()
    assert dashboard["driver"]["status"] == "on_mission"
    assert dashboard["available_missions_count"] == 0
    assert dashboard["active_mission"]["id"] == task["id"]


def test_available_preview_requires_driver_availability(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=58)).isoformat()
    _, order = create_ready_order(client, login, service_date)

    driver_available = make_driver_available(client, DRIVER_1_PHONE)
    offers = client.get(
        "/api/v1/driver/missions/available",
        headers=driver_available["headers"],
    ).json()
    task = next(x for x in offers if x["order_id"] == order["id"])

    driver_offline = login_phone(client, DRIVER_2_PHONE)
    response = client.get(
        f"/api/v1/driver/missions/available/{task['id']}",
        headers=driver_offline["headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "driver_not_available"


def test_photo_delivery_proof_uses_private_ready_media_asset(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=59)).isoformat()
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

    assert client.post(
        f"/api/v1/driver/missions/{task['id']}/accept",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{task['id']}/arrive-pickup",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{task['id']}/confirm-pickup",
        headers=driver["headers"],
    ).status_code == 200
    assert client.post(
        f"/api/v1/driver/missions/{task['id']}/start-delivery",
        headers=driver["headers"],
    ).status_code == 200

    proof_bytes = b"\xff\xd8\xff\xe0" + b"baytna-proof-photo" * 20

    created = client.post(
        "/api/v1/media/uploads",
        headers=driver["headers"],
        json={
            "purpose": "delivery_proof",
            "visibility": "private",
            "filename": "proof.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": len(proof_bytes),
        },
    )
    assert created.status_code == 201
    upload = created.json()
    assert upload["asset"]["purpose"] == "delivery_proof"
    assert upload["asset"]["visibility"] == "private"

    uploaded = client.put(
        upload["upload_url"],
        content=proof_bytes,
        headers=upload["upload_headers"],
    )
    assert uploaded.status_code == 200

    completed = client.post(
        f"/api/v1/media/{upload['asset']['id']}/complete",
        headers=driver["headers"],
    )
    assert completed.status_code == 200
    assert completed.json()["asset"]["status"] == "ready"

    delivered = client.post(
        f"/api/v1/driver/missions/{task['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "photo",
            "proof_reference": None,
            "media_asset_id": upload["asset"]["id"],
        },
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert (
        delivered.json()["delivery_proof_media_asset_id"]
        == upload["asset"]["id"]
    )


def test_driver_dashboard_completed_count_increases(login):
    client = login["client"]
    service_date = (date.today() + timedelta(days=60)).isoformat()
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
    client.post(f"/api/v1/driver/missions/{task['id']}/accept", headers=driver["headers"])
    client.post(f"/api/v1/driver/missions/{task['id']}/arrive-pickup", headers=driver["headers"])
    client.post(f"/api/v1/driver/missions/{task['id']}/confirm-pickup", headers=driver["headers"])
    client.post(f"/api/v1/driver/missions/{task['id']}/start-delivery", headers=driver["headers"])
    client.post(
        f"/api/v1/driver/missions/{task['id']}/deliver",
        headers=driver["headers"],
        json={
            "proof_type": "otp",
            "proof_reference": "4821",
        },
    )

    dashboard = client.get(
        "/api/v1/driver/app-dashboard",
        headers=driver["headers"],
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["completed_missions_count"] >= 1
