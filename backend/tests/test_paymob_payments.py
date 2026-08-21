import io
import json
import urllib.error
import urllib.parse
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    PaymentEntity,
    PaymentProviderTransactionEntity,
    PaymentReconciliationIssueEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.payments.paymob import (
    calculate_paymob_transaction_hmac,
    parse_paymob_transaction,
    verify_paymob_transaction_hmac,
)
from app.modules.payments.provider import (
    PaymobPaymentProvider,
    ProviderBillingData,
    ProviderLineItem,
    ProviderPaymentContext,
)
from app.modules.reliability.jobs import BackgroundJobService
from scripts.pilot_preflight import validate_pilot


CHEF_PHONE = "+201000000001"


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


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


def admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        admin = UserEntity(
            id=uuid4(),
            phone=f"+20104{uuid4().int % 100000000:08d}",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        token, _ = create_access_token(
            user_id=admin.id,
            role=UserRole.ADMIN,
            settings=settings,
        )
        return {"Authorization": f"Bearer {token}"}


def create_pending_order(client, customer, day_offset=20):
    service_date = (date.today() + timedelta(days=day_offset)).isoformat()
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
                    "quantity_total": 10,
                    "max_per_order": 10,
                }
            ],
        },
    )
    menu_item = published.json()["items"][0]

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer["headers"],
        json={
            "daily_menu_item_id": menu_item["id"],
            "quantity": 2,
        },
    )
    assert cart.status_code == 201

    order = client.post(
        "/api/v1/customer/orders",
        headers=customer["headers"],
        json={"cart_id": cart.json()["id"]},
    )
    assert order.status_code == 201
    return order.json()


class PaymobSettingsGuard:
    def __init__(self):
        self.settings = get_settings()
        self.values = {}

    def __enter__(self):
        fields = {
            "payment_provider": "paymob",
            "paymob_base_url": "https://accept.paymob.com",
            "paymob_secret_key": "paymob-secret-key-test-value",
            "paymob_public_key": "paymob-public-key-test-value",
            "paymob_hmac_secret": "paymob-hmac-test-value",
            "paymob_payment_methods": "12345,card",
            "paymob_notification_url": "https://api.test/api/v1/payments/webhooks/paymob/transaction",
            "paymob_redirection_url": "https://app.test/payment/result",
            "paymob_refund_enabled": False,
        }
        for key, value in fields.items():
            self.values[key] = getattr(self.settings, key)
            setattr(self.settings, key, value)
        return self.settings

    def __exit__(self, *args):
        for key, value in self.values.items():
            setattr(self.settings, key, value)


def paymob_obj(
    *,
    tx_id: int,
    payment_id: str,
    amount_minor: int,
    success: bool,
    pending: bool = False,
    order_id: int = 70001,
    is_refund: bool = False,
    parent_transaction: int | None = None,
    refunded_amount_cents: int = 0,
):
    return {
        "amount_cents": amount_minor,
        "created_at": "2026-08-11T00:00:00.000000",
        "currency": "EGP",
        "error_occured": False,
        "has_parent_transaction": parent_transaction is not None,
        "id": tx_id,
        "integration_id": 12345,
        "is_3d_secure": True,
        "is_auth": False,
        "is_capture": False,
        "is_refunded": refunded_amount_cents > 0,
        "is_standalone_payment": True,
        "is_voided": False,
        "order": {
            "id": order_id,
            "merchant_order_id": payment_id,
        },
        "owner": 99,
        "pending": pending,
        "source_data": {
            "pan": "2346",
            "sub_type": "MasterCard",
            "type": "card",
        },
        "success": success,
        "is_refund": is_refund,
        "is_void": False,
        "parent_transaction": parent_transaction,
        "refunded_amount_cents": refunded_amount_cents,
    }


def post_paymob_callback(client, obj: dict, secret: str):
    hmac_value = calculate_paymob_transaction_hmac(obj, secret)
    return client.post(
        f"/api/v1/payments/webhooks/paymob/transaction?hmac={hmac_value}",
        content=json.dumps({"type": "TRANSACTION", "obj": obj}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def test_paymob_intention_request_and_checkout_url(monkeypatch):
    settings = Settings(
        payment_provider="paymob",
        paymob_secret_key="secret-key",
        paymob_public_key="public-key",
        paymob_hmac_secret="hmac-secret",
        paymob_payment_methods="12345,67890",
        paymob_notification_url="https://api.test/paymob",
        paymob_redirection_url="https://app.test/result",
    )
    provider = PaymobPaymentProvider(settings)
    seen = {}

    def fake_urlopen(request, timeout=15):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "id": "pi_test_123",
                "client_secret": "client_secret_abc",
                "intention_order_id": 555123,
                "status": "created",
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    payment_id = uuid4()
    context = ProviderPaymentContext(
        order_id=uuid4(),
        customer_id=uuid4(),
        billing_data=ProviderBillingData(
            first_name="Ahmed",
            last_name="Ali",
            phone_number="+201001234567",
            email="ahmed@example.com",
        ),
        items=[
            ProviderLineItem(
                name="محشي",
                amount_minor=15000,
                quantity=2,
            )
        ],
        notification_url="https://api.test/paymob",
        redirection_url="https://app.test/result",
    )

    result = provider.create_intent(
        payment_id=payment_id,
        amount_minor=30000,
        currency="EGP",
        idempotency_key="paymob-intent-001",
        context=context,
    )

    assert seen["url"] == "https://accept.paymob.com/v1/intention/"
    assert seen["headers"]["Authorization"] == "Token secret-key"
    assert seen["payload"]["amount"] == 30000
    assert seen["payload"]["currency"] == "EGP"
    assert seen["payload"]["payment_methods"] == [12345, 67890]
    assert seen["payload"]["special_reference"] == str(payment_id)
    assert seen["payload"]["billing_data"]["phone_number"] == "+201001234567"
    assert seen["payload"]["items"][0]["quantity"] == 2
    parsed = urllib.parse.urlparse(result.checkout_url)
    query = urllib.parse.parse_qs(parsed.query)
    assert query["publicKey"] == ["public-key"]
    assert query["clientSecret"] == ["client_secret_abc"]
    assert result.reference == "pi_test_123"
    assert result.provider_order_reference == "555123"


def test_paymob_intention_falls_back_to_payable_total_item(monkeypatch):
    settings = Settings(
        payment_provider="paymob",
        paymob_secret_key="secret-key",
        paymob_public_key="public-key",
        paymob_hmac_secret="hmac-secret",
        paymob_payment_methods="12345",
    )
    provider = PaymobPaymentProvider(settings)
    seen = {}

    def fake_urlopen(request, timeout=15):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {"id": "pi_2", "client_secret": "cs_2"}
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider.create_intent(
        payment_id=uuid4(),
        amount_minor=31000,
        currency="EGP",
        idempotency_key="paymob-intent-total-fallback",
        context=ProviderPaymentContext(
            order_id=uuid4(),
            customer_id=uuid4(),
            billing_data=ProviderBillingData(
                first_name="A",
                last_name="B",
                phone_number="+201000000000",
                email="x@example.com",
            ),
            items=[
                ProviderLineItem(
                    name="Dish",
                    amount_minor=30000,
                    quantity=1,
                )
            ],
        ),
    )
    assert len(seen["payload"]["items"]) == 1
    assert seen["payload"]["items"][0]["amount"] == 31000


def test_paymob_hmac_is_deterministic_and_rejects_changes():
    obj = paymob_obj(
        tx_id=1001,
        payment_id=str(uuid4()),
        amount_minor=25000,
        success=True,
    )
    secret = "paymob-hmac-secret"
    value = calculate_paymob_transaction_hmac(obj, secret)
    assert len(value) == 128
    assert verify_paymob_transaction_hmac(
        obj,
        provided_hmac=value,
        secret=secret,
    )
    changed = dict(obj)
    changed["amount_cents"] = 25001
    assert not verify_paymob_transaction_hmac(
        changed,
        provided_hmac=value,
        secret=secret,
    )


def test_paymob_callback_success_confirms_order_and_records_provider_tx(
    login,
    monkeypatch,
):
    client = login["client"]
    with PaymobSettingsGuard() as settings:
        def fake_urlopen(request, timeout=15):
            return FakeResponse(
                {
                    "id": "pi_success_1",
                    "client_secret": "cs_success_1",
                    "intention_order_id": 88001,
                    "status": "created",
                }
            )
        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        order = create_pending_order(client, login, day_offset=34)
        intent = client.post(
            f"/api/v1/customer/orders/{order['id']}/payment-intent",
            headers=login["headers"],
            json={"idempotency_key": "paymob-success-intent-001"},
        )
        assert intent.status_code == 201, intent.text
        body = intent.json()
        assert body["provider"] == "paymob"
        assert body["provider_order_reference"] == "88001"

        obj = paymob_obj(
            tx_id=99001,
            payment_id=body["id"],
            amount_minor=body["amount_minor"],
            success=True,
            order_id=88001,
        )
        callback = post_paymob_callback(
            client,
            obj,
            settings.paymob_hmac_secret,
        )
        assert callback.status_code == 200, callback.text
        assert callback.json()["matched"] is True
        assert callback.json()["status"] == "processed"

        detail = client.get(
            f"/api/v1/customer/orders/{order['id']}",
            headers=login["headers"],
        )
        assert detail.json()["status"] == "confirmed"

        payment = client.get(
            f"/api/v1/customer/orders/{order['id']}/payment",
            headers=login["headers"],
        ).json()
        assert payment["status"] == "succeeded"
        assert payment["provider_transaction_reference"] == "99001"
        assert payment["provider_status"] == "succeeded"

        with SessionLocal() as db:
            tx = db.scalar(
                select(PaymentProviderTransactionEntity).where(
                    PaymentProviderTransactionEntity.provider_transaction_id
                    == "99001"
                )
            )
            assert tx is not None
            assert tx.payment_id == UUID(body["id"])
            assert tx.success is True


def test_duplicate_paymob_callback_is_idempotent(login, monkeypatch):
    client = login["client"]
    with PaymobSettingsGuard() as settings:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: FakeResponse(
                {
                    "id": "pi_dup_1",
                    "client_secret": "cs_dup_1",
                    "intention_order_id": 88002,
                }
            ),
        )
        order = create_pending_order(client, login, day_offset=35)
        intent = client.post(
            f"/api/v1/customer/orders/{order['id']}/payment-intent",
            headers=login["headers"],
            json={"idempotency_key": "paymob-duplicate-intent-001"},
        ).json()
        obj = paymob_obj(
            tx_id=99002,
            payment_id=intent["id"],
            amount_minor=intent["amount_minor"],
            success=True,
            order_id=88002,
        )
        first = post_paymob_callback(client, obj, settings.paymob_hmac_secret)
        second = post_paymob_callback(client, obj, settings.paymob_hmac_secret)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True

        with SessionLocal() as db:
            rows = list(
                db.scalars(
                    select(PaymentProviderTransactionEntity).where(
                        PaymentProviderTransactionEntity.provider_transaction_id
                        == "99002"
                    )
                ).all()
            )
            assert len(rows) == 1


def test_bad_paymob_hmac_is_rejected(client):
    settings = get_settings()
    old = settings.paymob_hmac_secret
    settings.paymob_hmac_secret = "valid-secret"
    try:
        obj = paymob_obj(
            tx_id=99003,
            payment_id=str(uuid4()),
            amount_minor=1000,
            success=True,
        )
        response = client.post(
            "/api/v1/payments/webhooks/paymob/transaction?hmac=bad",
            json={"type": "TRANSACTION", "obj": obj},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "paymob_webhook_hmac_invalid"
    finally:
        settings.paymob_hmac_secret = old


def test_unmatched_paymob_transaction_opens_reconciliation_issue(client):
    settings = get_settings()
    old = settings.paymob_hmac_secret
    settings.paymob_hmac_secret = "unmatched-hmac-secret"
    try:
        obj = paymob_obj(
            tx_id=99100,
            payment_id=str(uuid4()),
            amount_minor=43000,
            success=True,
            order_id=88999,
        )
        response = post_paymob_callback(
            client,
            obj,
            settings.paymob_hmac_secret,
        )
        assert response.status_code == 200
        assert response.json()["matched"] is False
        assert response.json()["issues_detected"] >= 1

        with SessionLocal() as db:
            issue = db.scalar(
                select(PaymentReconciliationIssueEntity).where(
                    PaymentReconciliationIssueEntity.issue_type
                    == "unmatched_provider_transaction"
                )
            )
            assert issue is not None
            assert issue.status == "open"
    finally:
        settings.paymob_hmac_secret = old


def test_paymob_amount_mismatch_creates_issue_without_confirming_order(
    login,
    monkeypatch,
):
    client = login["client"]
    with PaymobSettingsGuard() as settings:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: FakeResponse(
                {
                    "id": "pi_mismatch_1",
                    "client_secret": "cs_mismatch_1",
                    "intention_order_id": 88003,
                }
            ),
        )
        order = create_pending_order(client, login, day_offset=36)
        intent = client.post(
            f"/api/v1/customer/orders/{order['id']}/payment-intent",
            headers=login["headers"],
            json={"idempotency_key": "paymob-mismatch-intent-001"},
        ).json()

        obj = paymob_obj(
            tx_id=99004,
            payment_id=intent["id"],
            amount_minor=intent["amount_minor"] + 1,
            success=True,
            order_id=88003,
        )
        response = post_paymob_callback(
            client,
            obj,
            settings.paymob_hmac_secret,
        )
        assert response.status_code == 200
        assert response.json()["issues_detected"] >= 1

        detail = client.get(
            f"/api/v1/customer/orders/{order['id']}",
            headers=login["headers"],
        )
        assert detail.json()["status"] == "pending_payment"

        with SessionLocal() as db:
            issue = db.scalar(
                select(PaymentReconciliationIssueEntity).where(
                    PaymentReconciliationIssueEntity.issue_type
                    == "amount_mismatch"
                )
            )
            assert issue is not None


def test_failed_paymob_callback_maps_to_payment_failure(login, monkeypatch):
    client = login["client"]
    with PaymobSettingsGuard() as settings:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: FakeResponse(
                {
                    "id": "pi_failed_1",
                    "client_secret": "cs_failed_1",
                    "intention_order_id": 88004,
                }
            ),
        )
        order = create_pending_order(client, login, day_offset=37)
        intent = client.post(
            f"/api/v1/customer/orders/{order['id']}/payment-intent",
            headers=login["headers"],
            json={"idempotency_key": "paymob-failure-intent-001"},
        ).json()
        obj = paymob_obj(
            tx_id=99005,
            payment_id=intent["id"],
            amount_minor=intent["amount_minor"],
            success=False,
            pending=False,
            order_id=88004,
        )
        response = post_paymob_callback(
            client,
            obj,
            settings.paymob_hmac_secret,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

        payment = client.get(
            f"/api/v1/customer/orders/{order['id']}/payment",
            headers=login["headers"],
        ).json()
        assert payment["status"] == "failed"


def test_paymob_refund_request_builder(monkeypatch):
    settings = Settings(
        payment_provider="paymob",
        paymob_secret_key="secret-key",
        paymob_public_key="public-key",
        paymob_hmac_secret="hmac-secret",
        paymob_payment_methods="12345",
        paymob_refund_enabled=True,
        paymob_api_key="legacy-api-key",
    )
    provider = PaymobPaymentProvider(settings)
    seen = []

    def fake_urlopen(request, timeout=15):
        payload = json.loads(request.data.decode("utf-8"))
        seen.append((request.full_url, payload))
        if request.full_url.endswith("/api/auth/tokens"):
            return FakeResponse({"token": "legacy-auth-token"})
        return FakeResponse(
            {
                "id": 44401,
                "success": True,
                "is_refund": True,
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = provider.refund(
        payment_reference="99001",
        amount_minor=10000,
        idempotency_key="paymob-refund-001",
    )
    assert result.succeeded is True
    assert result.reference == "44401"
    assert seen[0][1]["api_key"] == "legacy-api-key"
    assert seen[1][1]["transaction_id"] == 99001
    assert seen[1][1]["amount_cents"] == 10000


def test_admin_reconciliation_api_and_resolve(client):
    settings = get_settings()
    old = settings.paymob_hmac_secret
    settings.paymob_hmac_secret = "admin-recon-hmac-secret"
    try:
        obj = paymob_obj(
            tx_id=99200,
            payment_id=str(uuid4()),
            amount_minor=15000,
            success=True,
            order_id=89200,
        )
        post_paymob_callback(client, obj, settings.paymob_hmac_secret)

        denied = client.get("/api/v1/admin/payments/reconciliation/summary")
        assert denied.status_code == 401

        headers = admin_headers()
        summary = client.get(
            "/api/v1/admin/payments/reconciliation/summary",
            headers=headers,
        )
        assert summary.status_code == 200
        assert summary.json()["issues_by_status"]["open"] >= 1

        issues = client.get(
            "/api/v1/admin/payments/reconciliation/issues?status=open",
            headers=headers,
        )
        assert issues.status_code == 200
        issue_id = issues.json()[0]["id"]

        resolved = client.post(
            f"/api/v1/admin/payments/reconciliation/issues/{issue_id}/resolve",
            headers=headers,
            json={"note": "تمت المراجعة اليدوية مع Paymob"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"
    finally:
        settings.paymob_hmac_secret = old



def test_paymob_refund_callback_confirms_pending_local_refund(login, monkeypatch):
    client = login["client"]
    with PaymobSettingsGuard() as settings:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: FakeResponse(
                {
                    "id": "pi_refund_callback",
                    "client_secret": "cs_refund_callback",
                    "intention_order_id": 88008,
                }
            ),
        )
        order = create_pending_order(client, login, day_offset=38)
        intent = client.post(
            f"/api/v1/customer/orders/{order['id']}/payment-intent",
            headers=login["headers"],
            json={"idempotency_key": "paymob-refund-callback-intent"},
        ).json()

        payment_obj = paymob_obj(
            tx_id=99008,
            payment_id=intent["id"],
            amount_minor=intent["amount_minor"],
            success=True,
            order_id=88008,
        )
        payment_callback = post_paymob_callback(
            client,
            payment_obj,
            settings.paymob_hmac_secret,
        )
        assert payment_callback.status_code == 200

        from app.core.db_models import RefundEntity

        refund_amount = max(1, intent["amount_minor"] // 2)
        with SessionLocal() as db:
            refund = RefundEntity(
                order_id=UUID(order["id"]),
                payment_id=UUID(intent["id"]),
                requested_by_user_id=UUID(login["body"]["user"]["id"]),
                amount_minor=refund_amount,
                reason="provider callback test",
                idempotency_key="paymob-refund-callback-001",
                status="pending",
            )
            db.add(refund)
            db.commit()
            refund_id = refund.id

        refund_obj = paymob_obj(
            tx_id=99108,
            payment_id=intent["id"],
            amount_minor=refund_amount,
            success=True,
            order_id=88008,
            is_refund=True,
            parent_transaction=99008,
            refunded_amount_cents=refund_amount,
        )
        refund_callback = post_paymob_callback(
            client,
            refund_obj,
            settings.paymob_hmac_secret,
        )
        assert refund_callback.status_code == 200
        assert refund_callback.json()["status"] == "processed"

        with SessionLocal() as db:
            refund = db.get(RefundEntity, refund_id)
            payment = db.get(PaymentEntity, UUID(intent["id"]))
            assert refund.status == "succeeded"
            assert refund.provider_reference == "99108"
            assert payment.refunded_minor == refund_amount
            mismatch = db.scalar(
                select(PaymentReconciliationIssueEntity).where(
                    PaymentReconciliationIssueEntity.payment_id == payment.id,
                    PaymentReconciliationIssueEntity.issue_type
                    == "refund_mismatch",
                )
            )
            assert mismatch is None

def test_worker_schedules_payment_reconciliation(login):
    with SessionLocal() as db:
        jobs = BackgroundJobService(db, get_settings()).schedule_maintenance()
        assert any(x.job_type == "payments.reconcile" for x in jobs)


def test_pilot_preflight_requires_paymob():
    settings = Settings(
        env="staging",
        database_url="postgresql+psycopg://baytna:x@db:5432/baytna",
        dev_return_otp=False,
        seed_demo_data=False,
        storage_provider="s3",
        storage_bucket="baytna-pilot",
        notification_push_provider="fcm",
        fcm_project_id="baytna-pilot",
        notification_sms_provider="twilio",
        twilio_account_sid="AC12345678901234567890123456789012",
        twilio_auth_token="twilio-token",
        twilio_from_number="+15005550006",
        twilio_status_callback_url="https://pilot.example/twilio",
        pilot_public_base_url="https://pilot.example",
    )
    problems = validate_pilot(settings)
    assert any("payment provider must be paymob" in x for x in problems)


def test_pilot_preflight_accepts_paymob_shape():
    settings = Settings(
        env="staging",
        database_url="postgresql+psycopg://baytna:x@db:5432/baytna",
        dev_return_otp=False,
        seed_demo_data=False,
        payment_provider="paymob",
        paymob_secret_key="paymob-secret-key",
        paymob_public_key="paymob-public-key",
        paymob_hmac_secret="paymob-hmac-secret",
        paymob_payment_methods="12345",
        paymob_notification_url="https://pilot.example/api/v1/payments/webhooks/paymob/transaction",
        paymob_redirection_url="https://pilot.example/payment/result",
        storage_provider="s3",
        storage_bucket="baytna-pilot",
        notification_push_provider="fcm",
        fcm_project_id="baytna-pilot",
        notification_sms_provider="twilio",
        twilio_account_sid="AC12345678901234567890123456789012",
        twilio_auth_token="twilio-token",
        twilio_from_number="+15005550006",
        twilio_status_callback_url="https://pilot.example/twilio",
        pilot_public_base_url="https://pilot.example",
    )
    assert validate_pilot(settings) == []


def test_production_accepts_paymob_configuration():
    settings = Settings(
        env="production",
        database_url="postgresql+psycopg://baytna:strong@db:5432/baytna",
        cors_origins="https://app.baytna.example",
        allowed_hosts="api.baytna.example",
        security_hsts_enabled=True,
        expansion_rollout_required=True,
        traffic_require_delivery_address_for_checkout=True,
        vendor_accounting_require_dual_control=True,
        vendor_accounting_require_closed_settlements_for_rollout=True,
        launch_command_required=True,
        launch_command_require_dual_control=True,
        slo_auto_pause_default_enabled=True,
        launch_daily_close_cadence_enabled=True,
        dev_return_otp=False,
        seed_demo_data=False,
        payment_provider="paymob",
        paymob_secret_key="S" * 48,
        paymob_public_key="pk_live_example",
        paymob_hmac_secret="H" * 48,
        paymob_payment_methods="12345",
        paymob_notification_url="https://api.baytna.example/api/v1/payments/webhooks/paymob/transaction",
        paymob_redirection_url="https://app.baytna.example/payment/result",
        jwt_secret="J" * 48,
        otp_pepper="O" * 48,
        refresh_token_pepper="R" * 48,
        payment_webhook_secret="P" * 48,
        storage_provider="s3",
        storage_bucket="baytna-production",
        media_signing_secret="M" * 48,
        integration_encryption_secret="I" * 48,
        notification_provider_webhook_secret="W" * 48,
        notification_push_provider="fcm",
        fcm_project_id="baytna-production",
        notification_sms_provider="twilio",
        twilio_account_sid="AC12345678901234567890123456789012",
        twilio_auth_token="T" * 48,
        twilio_from_number="+15005550006",
        twilio_status_callback_url="https://api.baytna.example/twilio",
    )
    assert settings.payment_provider == "paymob"
