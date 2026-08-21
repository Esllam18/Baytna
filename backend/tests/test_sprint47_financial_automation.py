from __future__ import annotations

import json
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    EconomicsCostEntryEntity,
    ExpansionZoneBudgetEntity,
    PaymentEntity,
    PaymentProviderTransactionEntity,
    PaymentReconciliationIssueEntity,
    ProviderSettlementBatchEntity,
)
from app.core.security import utc_now
from app.modules.reliability.jobs import BackgroundJobService
from tests.test_admin_operations import admin_headers, make_order
from tests.test_sprint46_operational_economics import (
    _completed_profitable_program,
)


class FakeHttpResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _paymob_ledger(
    client,
    *,
    tx_id: str,
    amount_minor: int = 30000,
):
    order_id, customer_id = make_order(
        client,
        status="delivered",
        total=amount_minor,
        with_payment=False,
    )
    with SessionLocal() as db:
        payment = PaymentEntity(
            order_id=order_id,
            customer_id=customer_id,
            provider="paymob",
            provider_reference=f"pi-{tx_id}",
            provider_order_reference=f"po-{tx_id}",
            provider_transaction_reference=tx_id,
            provider_status="succeeded",
            provider_last_seen_at=utc_now(),
            idempotency_key=f"s47-pay-{tx_id}",
            amount_minor=amount_minor,
            refunded_minor=0,
            currency="EGP",
            status="succeeded",
            expires_at=utc_now() + timedelta(hours=1),
            succeeded_at=utc_now(),
        )
        db.add(payment)
        db.flush()
        db.add(
            PaymentProviderTransactionEntity(
                provider="paymob",
                provider_transaction_id=tx_id,
                payment_id=payment.id,
                provider_order_reference=f"po-{tx_id}",
                transaction_type="payment",
                amount_minor=amount_minor,
                currency="EGP",
                success=True,
                pending=False,
                is_refunded=False,
                refunded_minor=0,
                payload_hash=f"hash-{tx_id}",
                payload_json={"id": tx_id},
                observed_at=utc_now(),
            )
        )
        db.commit()
        return order_id, payment.id


def _approved_zone(client, area: str = "الشيخ زايد Sprint47"):
    headers, program = _completed_profitable_program(client)
    created = client.post(
        "/api/v1/admin/economics/zones",
        headers=headers,
        json={
            "area": area,
            "source_program_id": program["id"],
            "min_delivered_orders": 40,
            "min_contribution_margin_pct": 5,
            "min_operational_profit_minor": 1,
            "notes": "Sprint 47 controlled rollout fixture",
        },
    )
    assert created.status_code == 201, created.text
    zone = created.json()
    assessed = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/assess",
        headers=headers,
    )
    assert assessed.status_code == 200, assessed.text
    assert assessed.json()["decision"] == "ready"
    approved = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    return headers, program, approved.json()


def _fund_required_budgets(client, headers, zone_id: str):
    for category in [
        "operations",
        "chef_onboarding",
        "delivery_supply",
        "contingency",
    ]:
        response = client.put(
            f"/api/v1/admin/economics/zones/{zone_id}/budgets",
            headers=headers,
            json={
                "category": category,
                "allocated_minor": 100000,
                "note": "Sprint 47 rollout budget",
            },
        )
        assert response.status_code == 200, response.text


def test_customer_cannot_access_financial_automation(login):
    response = login["client"].get(
        "/api/v1/admin/economics/imports",
        headers=login["headers"],
    )
    assert response.status_code == 403

    response = login["client"].get(
        "/api/v1/admin/economics/settlements",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_provider_import_validate_apply_creates_verified_cost(client):
    headers, _ = admin_headers()
    order_id, _ = make_order(client, status="delivered", total=30000)

    created = client.post(
        "/api/v1/admin/economics/imports",
        headers=headers,
        json={
            "provider": "courier_partner",
            "pilot_program_id": None,
            "area": "6 October",
            "period_start": date.today().isoformat(),
            "period_end": date.today().isoformat(),
            "source_currency": "EGP",
            "fx_rate_to_egp": None,
            "fx_reference": None,
            "external_reference": "s47-courier-import-001",
            "lines": [
                {
                    "line_key": "line-001",
                    "order_id": str(order_id),
                    "incurred_on": date.today().isoformat(),
                    "cost_type": "delivery_partner",
                    "source_amount_minor": 3500,
                    "external_reference": "courier-line-001",
                    "description": "Actual courier cost",
                    "raw_json": {"provider": "fixture"},
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["batch"]["status"] == "draft"

    validated = client.post(
        f"/api/v1/admin/economics/imports/{created.json()['batch']['id']}/validate",
        headers=headers,
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["batch"]["status"] == "validated"

    applied = client.post(
        f"/api/v1/admin/economics/imports/{created.json()['batch']['id']}/apply",
        headers=headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["batch"]["status"] == "applied"
    assert applied.json()["batch"]["applied_cost_entries"] == 1

    with SessionLocal() as db:
        cost = db.scalar(
            select(EconomicsCostEntryEntity).where(
                EconomicsCostEntryEntity.external_reference
                == "provider-import:courier_partner:"
                "s47-courier-import-001:line-001"
            )
        )
        assert cost is not None
        assert cost.amount_minor == 3500
        assert cost.source == "provider"
        assert cost.is_verified is True
        assert cost.order_id == order_id


def test_non_egp_provider_import_requires_explicit_fx_and_reference(client):
    headers, _ = admin_headers()
    base = {
        "provider": "cloud_vendor",
        "pilot_program_id": None,
        "area": None,
        "period_start": date.today().isoformat(),
        "period_end": date.today().isoformat(),
        "source_currency": "USD",
        "external_reference": "s47-usd-import-001",
        "lines": [
            {
                "line_key": "usd-line-1",
                "order_id": None,
                "incurred_on": date.today().isoformat(),
                "cost_type": "cloud_infrastructure",
                "source_amount_minor": 125,
                "raw_json": {},
            }
        ],
    }

    rejected = client.post(
        "/api/v1/admin/economics/imports",
        headers=headers,
        json={**base, "fx_rate_to_egp": None, "fx_reference": None},
    )
    assert rejected.status_code == 422

    accepted = client.post(
        "/api/v1/admin/economics/imports",
        headers=headers,
        json={
            **base,
            "external_reference": "s47-usd-import-002",
            "fx_rate_to_egp": 50,
            "fx_reference": "bank-rate-2026-08-13",
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["batch"]["total_source_minor"] == 125
    assert accepted.json()["batch"]["total_egp_minor"] == 6250
    assert accepted.json()["lines"][0]["egp_amount_minor"] == 6250


def test_twilio_usage_adapter_creates_draft_import_with_explicit_fx(client, monkeypatch):
    headers, _ = admin_headers()
    settings = get_settings()
    old_sid = settings.twilio_account_sid
    old_token = settings.twilio_auth_token
    old_base = settings.twilio_api_base_url
    seen = {}

    def fake_urlopen(request, timeout=20):
        seen["url"] = request.full_url
        seen["authorization"] = request.headers.get("Authorization")
        return FakeHttpResponse(
            {
                "usage_records": [
                    {
                        "category": "totalprice",
                        "description": "Total Price",
                        "start_date": date.today().isoformat(),
                        "end_date": date.today().isoformat(),
                        "price": "-1.25",
                        "price_unit": "usd",
                        "uri": "/2010-04-01/Accounts/AC_TEST/Usage/Records.json",
                    }
                ]
            }
        )

    settings.twilio_account_sid = "AC_SPRINT47_TEST"
    settings.twilio_auth_token = "sprint47-twilio-token"
    settings.twilio_api_base_url = "https://api.twilio.com/2010-04-01"
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    try:
        response = client.post(
            "/api/v1/admin/economics/providers/twilio/sync",
            headers=headers,
            json={
                "pilot_program_id": None,
                "area": None,
                "period_start": date.today().isoformat(),
                "period_end": date.today().isoformat(),
                "category": "totalprice",
                "fx_rate_to_egp": 50,
                "fx_reference": "documented-fx-rate",
                "external_reference": "twilio-usage-s47-001",
            },
        )
    finally:
        settings.twilio_account_sid = old_sid
        settings.twilio_auth_token = old_token
        settings.twilio_api_base_url = old_base

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["batch"]["provider"] == "twilio"
    assert body["batch"]["status"] == "draft"
    assert body["batch"]["source_currency"] == "USD"
    assert body["batch"]["total_source_minor"] == 125
    assert body["batch"]["total_egp_minor"] == 6250
    assert body["lines"][0]["cost_type"] == "communications_provider"
    assert "Usage/Records.json" in seen["url"]
    assert "Category=totalprice" in seen["url"]
    assert seen["authorization"].startswith("Basic ")


def test_paymob_settlement_reconciles_and_materializes_verified_fee_cost(client):
    headers, _ = admin_headers()
    order_id, _ = _paymob_ledger(
        client,
        tx_id="s47-paymob-tx-001",
        amount_minor=30000,
    )
    settled_at = utc_now().isoformat()

    created = client.post(
        "/api/v1/admin/economics/settlements",
        headers=headers,
        json={
            "provider": "paymob",
            "pilot_program_id": None,
            "period_start": date.today().isoformat(),
            "period_end": date.today().isoformat(),
            "currency": "EGP",
            "external_reference": "paymob-settlement-s47-001",
            "lines": [
                {
                    "provider_transaction_id": "s47-paymob-tx-001",
                    "settlement_reference": "set-line-001",
                    "gross_amount_minor": 30000,
                    "fee_minor": 750,
                    "refund_minor": 0,
                    "net_settlement_minor": 29250,
                    "is_settled": True,
                    "settled_at": settled_at,
                    "raw_json": {"source": "merchant settlement fixture"},
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    batch_id = created.json()["batch"]["id"]

    reconciled = client.post(
        f"/api/v1/admin/economics/settlements/{batch_id}/reconcile",
        headers=headers,
    )
    assert reconciled.status_code == 200, reconciled.text
    body = reconciled.json()
    assert body["batch"]["status"] == "reconciled"
    assert body["batch"]["matched_lines"] == 1
    assert body["batch"]["mismatched_lines"] == 0
    assert body["lines"][0]["reconciliation_status"] == "matched"

    with SessionLocal() as db:
        cost = db.scalar(
            select(EconomicsCostEntryEntity).where(
                EconomicsCostEntryEntity.external_reference
                == "settlement:paymob-settlement-s47-001:"
                "s47-paymob-tx-001:fee"
            )
        )
        assert cost is not None
        assert cost.order_id == order_id
        assert cost.cost_type == "payment_processing"
        assert cost.amount_minor == 750
        assert cost.is_verified is True


def test_paymob_settlement_mismatch_blocks_batch_and_creates_no_fee_cost(client):
    headers, _ = admin_headers()
    _paymob_ledger(
        client,
        tx_id="s47-paymob-tx-mismatch",
        amount_minor=30000,
    )
    created = client.post(
        "/api/v1/admin/economics/settlements",
        headers=headers,
        json={
            "provider": "paymob",
            "pilot_program_id": None,
            "period_start": date.today().isoformat(),
            "period_end": date.today().isoformat(),
            "currency": "EGP",
            "external_reference": "paymob-settlement-s47-bad",
            "lines": [
                {
                    "provider_transaction_id": "s47-paymob-tx-mismatch",
                    "gross_amount_minor": 29999,
                    "fee_minor": 750,
                    "refund_minor": 0,
                    "net_settlement_minor": 29249,
                    "is_settled": True,
                    "settled_at": utc_now().isoformat(),
                    "raw_json": {},
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    reconciled = client.post(
        f"/api/v1/admin/economics/settlements/{created.json()['batch']['id']}/reconcile",
        headers=headers,
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["batch"]["status"] == "blocked"
    assert "gross_amount_mismatch" in reconciled.json()["batch"]["blockers_json"]

    with SessionLocal() as db:
        cost = db.scalar(
            select(EconomicsCostEntryEntity).where(
                EconomicsCostEntryEntity.external_reference.like(
                    "settlement:paymob-settlement-s47-bad:%"
                )
            )
        )
        assert cost is None


def test_finance_settlement_reconciliation_is_worker_maintenance_job(client):
    with SessionLocal() as db:
        jobs = BackgroundJobService(
            db,
            get_settings(),
        ).schedule_maintenance()
        assert any(
            x.job_type == "finance.settlements.reconcile"
            for x in jobs
        )
        assert len(jobs) == 13


def test_zone_budget_enforces_required_categories_and_no_overspend(client):
    headers, _, zone = _approved_zone(
        client,
        "الشيخ زايد Budget Sprint47",
    )

    empty = client.get(
        f"/api/v1/admin/economics/zones/{zone['id']}/budgets",
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json()["budget_ready"] is False
    assert set(empty.json()["missing_categories"]) == {
        "operations",
        "chef_onboarding",
        "delivery_supply",
        "contingency",
    }

    _fund_required_budgets(client, headers, zone["id"])

    ready = client.get(
        f"/api/v1/admin/economics/zones/{zone['id']}/budgets",
        headers=headers,
    )
    assert ready.status_code == 200
    assert ready.json()["budget_ready"] is True
    budget = next(
        x
        for x in ready.json()["budgets"]
        if x["category"] == "operations"
    )

    committed = client.post(
        f"/api/v1/admin/economics/budgets/{budget['id']}/movement",
        headers=headers,
        json={"action": "commit", "amount_minor": 80000, "note": "supplier PO"},
    )
    assert committed.status_code == 200
    assert committed.json()["committed_minor"] == 80000

    rejected = client.post(
        f"/api/v1/admin/economics/budgets/{budget['id']}/movement",
        headers=headers,
        json={"action": "commit", "amount_minor": 30000, "note": "too much"},
    )
    assert rejected.status_code == 409


def test_controlled_zone_rollout_canary_limited_full_pause_resume(client):
    headers, _, zone = _approved_zone(
        client,
        "الشيخ زايد Rollout Sprint47",
    )

    blocked = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
        headers=headers,
        json={"daily_order_cap": 20},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "expansion_rollout_blocked"

    _fund_required_budgets(client, headers, zone["id"])

    canary = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
        headers=headers,
        json={"daily_order_cap": 20},
    )
    assert canary.status_code == 200, canary.text
    assert canary.json()["zone_status"] == "live"
    assert canary.json()["rollout_stage"] == "canary"
    assert canary.json()["rollout_percent"] == 10
    assert canary.json()["daily_order_cap"] == 20

    limited = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/advance",
        headers=headers,
        json={"daily_order_cap": 75},
    )
    assert limited.status_code == 200, limited.text
    assert limited.json()["rollout_stage"] == "limited"
    assert limited.json()["rollout_percent"] == 50

    paused = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/pause",
        headers=headers,
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["zone_status"] == "paused"
    assert paused.json()["rollout_stage"] == "paused"

    resumed = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/resume",
        headers=headers,
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["zone_status"] == "live"
    assert resumed.json()["rollout_stage"] == "limited"

    full = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/advance",
        headers=headers,
        json={"daily_order_cap": None},
    )
    assert full.status_code == 200, full.text
    assert full.json()["rollout_stage"] == "full"
    assert full.json()["rollout_percent"] == 100


def test_rollout_blocks_on_open_payment_reconciliation_issue(client):
    headers, _, zone = _approved_zone(
        client,
        "الشيخ زايد Finance Block Sprint47",
    )
    _fund_required_budgets(client, headers, zone["id"])

    with SessionLocal() as db:
        db.add(
            PaymentReconciliationIssueEntity(
                fingerprint="s47-open-reconciliation-blocker",
                payment_id=None,
                provider_transaction_id="unmatched-s47",
                issue_type="unmatched_provider_transaction",
                status="open",
                expected_json={},
                actual_json={"fixture": True},
                detected_at=utc_now(),
                last_detected_at=utc_now(),
            )
        )
        db.commit()

    response = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
        headers=headers,
        json={},
    )
    assert response.status_code == 409
    assert "payment_reconciliation_open" in response.json()["error"]["details"]["blockers"]


def test_rollout_blocks_on_blocked_source_program_settlement(client):
    headers, program, zone = _approved_zone(
        client,
        "الشيخ زايد Settlement Block Sprint47",
    )
    _fund_required_budgets(client, headers, zone["id"])

    with SessionLocal() as db:
        db.add(
            ProviderSettlementBatchEntity(
                provider="paymob",
                pilot_program_id=UUID(program["id"]),
                period_start=date.today(),
                period_end=date.today(),
                currency="EGP",
                external_reference="s47-blocked-rollout-settlement",
                checksum_sha256="a" * 64,
                status="blocked",
                rows_count=1,
                matched_lines=0,
                mismatched_lines=1,
                gross_minor=10000,
                fees_minor=100,
                refunds_minor=0,
                net_settlement_minor=9900,
                blockers_json=["gross_amount_mismatch"],
            )
        )
        db.commit()

    response = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
        headers=headers,
        json={},
    )
    assert response.status_code == 409
    assert (
        "blocked_provider_settlement_batches"
        in response.json()["error"]["details"]["blockers"]
    )


def test_legacy_direct_launch_is_blocked_when_rollout_required(client):
    headers, _, zone = _approved_zone(
        client,
        "الشيخ زايد Legacy Guard Sprint47",
    )
    settings = get_settings()
    old = settings.expansion_rollout_required
    settings.expansion_rollout_required = True
    try:
        response = client.post(
            f"/api/v1/admin/economics/zones/{zone['id']}/launch",
            headers=headers,
        )
    finally:
        settings.expansion_rollout_required = old

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "expansion_rollout_required"
