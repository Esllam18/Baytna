from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass


@dataclass
class Client:
    base_url: str
    token: str

    def request(self, method: str, path: str, payload: dict | None = None):
        url = self.base_url.rstrip("/") + path
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8") or "{}")


def public_get(base_url: str, path: str):
    with urllib.request.urlopen(base_url.rstrip("/") + path, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def register_test_device(client: Client, actor: str) -> None:
    token = os.environ.get(
        f"BAYTNA_STAGING_{actor.upper()}_FCM_TOKEN",
        "",
    ).strip()
    if not token:
        print(f"push/{actor}: SKIPPED (no device token)")
        return

    client.request(
        "POST",
        "/api/v1/notifications/devices",
        {
            "platform": "android",
            "token": token,
            "device_name": f"staging-{actor}",
            "app_version": "0.41.0",
        },
    )
    client.request(
        "PUT",
        "/api/v1/notifications/preferences",
        {
            "push_enabled": True,
            "sms_enabled": False,
            "order_updates": True,
            "support_updates": True,
            "marketing_enabled": False,
        },
    )
    print(f"push/{actor}: OK")


def main() -> int:
    base_url = os.environ["BAYTNA_STAGING_BASE_URL"].rstrip("/")
    customer = Client(
        base_url,
        os.environ["BAYTNA_STAGING_CUSTOMER_BEARER_TOKEN"],
    )
    chef = Client(
        base_url,
        os.environ["BAYTNA_STAGING_CHEF_BEARER_TOKEN"],
    )
    driver = Client(
        base_url,
        os.environ["BAYTNA_STAGING_DRIVER_BEARER_TOKEN"],
    )
    admin = Client(
        base_url,
        os.environ["BAYTNA_STAGING_ADMIN_BEARER_TOKEN"],
    )

    ready = public_get(base_url, "/health/ready")
    assert ready["status"] == "ready"
    print("1/8 API readiness: OK")

    customer_me = customer.request("GET", "/api/v1/me")
    chef_profile = chef.request("GET", "/api/v1/chef/profile")
    driver_profile = driver.request("GET", "/api/v1/driver/profile")
    admin_profile = admin.request("GET", "/api/v1/admin/profile")
    assert customer_me["role"] == "customer"
    assert chef_profile["id"]
    assert driver_profile["status"] in {"offline", "available", "on_mission"}
    assert admin_profile["role"] == "admin"
    print("2/8 four-role authentication: OK")

    for actor, client in [
        ("customer", customer),
        ("chef", chef),
        ("driver", driver),
    ]:
        register_test_device(client, actor)
    print("3/8 push registration checks: OK")

    integrations = admin.request(
        "GET",
        "/api/v1/admin/integrations/status",
    )
    assert integrations["notifications"]["push"]["configured"]
    assert integrations["storage"]["configured"]
    print("4/8 integration readiness: OK")

    order_id = os.environ.get(
        "BAYTNA_STAGING_CROSS_APP_ORDER_ID",
        "",
    ).strip()
    if not order_id:
        print(
            "5-8/8 cross-app live fulfillment: SKIPPED "
            "(set BAYTNA_STAGING_CROSS_APP_ORDER_ID to a paid confirmed pilot order)"
        )
        print("Sprint 41 staging cross-app preflight passed.")
        return 0

    chef_orders = chef.request("GET", "/api/v1/chef/orders")
    order = next(
        (x for x in chef_orders if x["order_id"] == order_id),
        None,
    )
    if order is None:
        raise RuntimeError("Configured order is not visible to the staging chef.")

    stage = order["fulfillment_stage"]
    if stage == "new":
        chef.request(
            "POST",
            f"/api/v1/chef/orders/{order_id}/accept",
            {"chef_note": "Sprint 41 staging cross-app validation"},
        )
        stage = "accepted"
    if stage == "accepted":
        chef.request(
            "POST",
            f"/api/v1/chef/orders/{order_id}/start-preparing",
            {"chef_note": "Sprint 41 staging cooking"},
        )
        stage = "preparing"
    if stage == "preparing":
        chef.request(
            "POST",
            f"/api/v1/chef/orders/{order_id}/start-packaging",
            {"chef_note": "Sprint 41 staging packaging"},
        )
        stage = "packaging"
    if stage == "packaging":
        chef.request(
            "POST",
            f"/api/v1/chef/orders/{order_id}/ready-for-pickup",
            {"chef_note": "Sprint 41 staging ready"},
        )
    print("5/8 chef fulfillment to ready: OK")

    status = driver.request("GET", "/api/v1/driver/status")
    if status["status"] == "offline":
        driver.request(
            "PUT",
            "/api/v1/driver/availability",
            {"available": True},
        )

    dashboard = driver.request("GET", "/api/v1/driver/app-dashboard")
    mission = dashboard.get("active_mission")
    if not mission:
        offers = driver.request(
            "GET",
            "/api/v1/driver/missions/available",
        )
        mission = next(
            (x for x in offers if x["order_id"] == order_id),
            None,
        )
        if mission is None:
            raise RuntimeError("Ready order did not produce a driver mission.")
        mission = driver.request(
            "POST",
            f"/api/v1/driver/missions/{mission['id']}/accept",
        )

    mission_id = mission["id"]
    state = mission["status"]
    if state == "to_pickup":
        mission = driver.request(
            "POST",
            f"/api/v1/driver/missions/{mission_id}/arrive-pickup",
        )
        state = mission["status"]
    if state == "at_pickup":
        mission = driver.request(
            "POST",
            f"/api/v1/driver/missions/{mission_id}/confirm-pickup",
        )
        state = mission["status"]
    if state == "picked_up":
        mission = driver.request(
            "POST",
            f"/api/v1/driver/missions/{mission_id}/start-delivery",
        )
        state = mission["status"]
    print("6/8 driver pickup and route start: OK")

    if state == "to_customer":
        proof = os.environ.get(
            "BAYTNA_STAGING_DELIVERY_PROOF_REFERENCE",
            "",
        ).strip()
        if not proof:
            raise RuntimeError(
                "Set BAYTNA_STAGING_DELIVERY_PROOF_REFERENCE "
                "before allowing the script to mark a real staging order delivered."
            )
        mission = driver.request(
            "POST",
            f"/api/v1/driver/missions/{mission_id}/deliver",
            {
                "proof_type": "manual",
                "proof_reference": proof,
            },
        )
        state = mission["status"]
    assert state == "delivered"
    print("7/8 delivery completion: OK")

    tracking = customer.request(
        "GET",
        f"/api/v1/customer/orders/{order_id}/tracking",
    )
    assert tracking["status"] == "delivered"

    admin_order = admin.request(
        "GET",
        f"/api/v1/admin/orders/{order_id}",
    )
    assert admin_order["order"]["status"] == "delivered"
    print("8/8 customer/admin delivered-state verification: OK")

    print("Sprint 41 staging cross-app validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
