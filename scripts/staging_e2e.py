from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass


@dataclass
class Client:
    base_url: str
    token: str

    def request(self, method: str, path: str, payload: dict | bytes | None = None):
        url = self.base_url.rstrip("/") + path
        headers = {"Authorization": f"Bearer {self.token}"}
        data = None
        if isinstance(payload, dict):
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif isinstance(payload, bytes):
            data = payload
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                return json.loads(raw.decode("utf-8") or "{}")
            return raw


def public_get(base_url: str, path: str):
    with urllib.request.urlopen(base_url.rstrip("/") + path, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    base_url = os.environ["BAYTNA_STAGING_BASE_URL"]
    customer_token = os.environ["BAYTNA_STAGING_CUSTOMER_BEARER_TOKEN"]
    admin_token = os.environ["BAYTNA_STAGING_ADMIN_BEARER_TOKEN"]

    customer = Client(base_url, customer_token)
    admin = Client(base_url, admin_token)

    ready = public_get(base_url, "/health/ready")
    assert ready["status"] == "ready"
    print("1/6 readiness: OK")

    me = customer.request("GET", "/api/v1/me")
    user_id = me["id"]
    print("2/6 customer authentication: OK")

    media_bytes = b"baytna-staging-media-check"
    upload = customer.request(
        "POST",
        "/api/v1/media/uploads",
        {
            "purpose": "customer_attachment",
            "visibility": "private",
            "filename": "staging-check.png",
            "mime_type": "image/png",
            "size_bytes": len(media_bytes),
        },
    )
    upload_url = upload["upload_url"]
    if upload_url.startswith("/"):
        upload_url = base_url.rstrip("/") + upload_url
    req = urllib.request.Request(
        upload_url,
        data=media_bytes,
        headers=upload.get("upload_headers") or {},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=30):
        pass
    completed = customer.request(
        "POST",
        f"/api/v1/media/{upload['asset']['id']}/complete",
    )
    assert completed["asset"]["status"] == "ready"
    print("3/6 object storage signed upload: OK")

    device_token = os.environ.get("BAYTNA_STAGING_FCM_DEVICE_TOKEN", "").strip()
    channels = []
    if device_token:
        customer.request(
            "POST",
            "/api/v1/customer/notifications/devices",
            {
                "platform": os.environ.get(
                    "BAYTNA_STAGING_DEVICE_PLATFORM",
                    "android",
                ),
                "token": device_token,
                "device_name": "staging-e2e",
                "app_version": "staging",
            },
        )
        channels.append("push")
    if os.environ.get("BAYTNA_STAGING_TEST_SMS", "false").lower() == "true":
        channels.append("sms")

    customer.request(
        "PUT",
        "/api/v1/customer/notifications/preferences",
        {
            "push_enabled": "push" in channels,
            "sms_enabled": "sms" in channels,
            "order_updates": True,
            "support_updates": True,
            "marketing_enabled": False,
        },
    )
    print("4/6 notification preferences/device registration: OK")

    status = admin.request("GET", "/api/v1/admin/integrations/status")
    assert status["notifications"]["push"]["configured"]
    assert status["notifications"]["sms"]["configured"]
    print("5/6 integration configuration: OK")

    if channels:
        result = admin.request(
            "POST",
            "/api/v1/admin/integrations/test-notification",
            {
                "user_id": user_id,
                "channels": channels,
                "title": "Baytna staging test",
                "body": "اختبار تكامل بيئة بيتنا التجريبية.",
                "dispatch_now": True,
            },
        )
        bad = [
            x
            for x in result.get("deliveries", [])
            if x["status"] not in {"succeeded", "retry"}
        ]
        if bad:
            raise RuntimeError(f"External delivery test failed: {bad}")
        print("6/7 real notification dispatch request: OK")
    else:
        print("6/7 external notification send: SKIPPED (no test target configured)")

    payment_order_id = os.environ.get(
        "BAYTNA_STAGING_PAYMENT_ORDER_ID",
        "",
    ).strip()
    if payment_order_id:
        payment = customer.request(
            "POST",
            f"/api/v1/customer/orders/{payment_order_id}/payment-intent",
            {"idempotency_key": "staging-paymob-validation-001"},
        )
        assert payment["provider"] == "paymob"
        assert payment["checkout_url"].startswith("https://")
        assert payment["provider_reference"]
        print("7/7 Paymob intention creation: OK (no charge auto-completed)")
    else:
        print("7/7 Paymob intention: SKIPPED (no test order configured)")

    print("Baytna staging E2E validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
