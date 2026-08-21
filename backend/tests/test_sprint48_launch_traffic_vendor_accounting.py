from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    EconomicsCostEntryEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionZoneEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    PaymentReconciliationIssueEntity,
    PilotProgramEntity,
    ProviderCostImportBatchEntity,
    ProviderSettlementBatchEntity,
    ProviderSettlementLineEntity,
    ZoneAdmissionEventEntity,
    ZoneTrafficPolicyEntity,
)
from app.core.security import utc_now
from app.modules.launch_governance.service import LaunchTrafficGovernanceService
from app.modules.reliability.jobs import BackgroundJobService
from tests.test_admin_operations import admin_headers
from tests.test_orders import (
    CHEF_1_ID,
    CHEF_1_PHONE,
    login_phone,
    publish_today_item,
)
from tests.test_sprint47_financial_automation import (
    _approved_zone,
    _fund_required_budgets,
    _paymob_ledger,
)


def _live_zone(
    *,
    area: str,
    daily_cap: int | None = 5,
    rollout_stage: str = "full",
    rollout_percent: int = 100,
    enforce_bucket: bool = False,
    hourly_cap: int | None = 50,
    chef_cap: int | None = 50,
):
    with SessionLocal() as db:
        program = PilotProgramEntity(
            name=f"Sprint48 traffic {uuid4()}",
            area="6 أكتوبر",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            status="completed",
            required_stability_weeks=8,
            rating_target=4.7,
            repeat_customer_target_pct=40,
            on_time_target_pct=95,
            cancellation_max_pct=5,
        )
        db.add(program)
        db.flush()
        zone = ExpansionZoneEntity(
            area=area,
            source_program_id=program.id,
            status="live" if rollout_stage != "paused" else "paused",
            min_delivered_orders=1,
            min_contribution_margin_pct=0,
            min_operational_profit_minor=1,
            rollout_stage=rollout_stage,
            rollout_percent=rollout_percent,
            daily_order_cap=daily_cap,
            rollout_started_at=utc_now(),
        )
        db.add(zone)
        db.flush()
        policy = ZoneTrafficPolicyEntity(
            zone_id=zone.id,
            is_enabled=True,
            hourly_order_cap=hourly_cap,
            chef_daily_order_cap=chef_cap,
            enforce_rollout_bucket=enforce_bucket,
            warning_utilization_pct=80,
            critical_utilization_pct=95,
            rejection_spike_pct=30,
            rejection_spike_min_attempts=2,
            note="Sprint 48 test policy",
        )
        db.add(policy)
        db.commit()
        return zone.id, program.id


def _address(client, customer, area: str, *, default=False):
    response = client.post(
        "/api/v1/customer/addresses",
        headers=customer["headers"],
        json={
            "label": area,
            "area": area,
            "street": "Test Street",
            "building": "1",
            "floor": "2",
            "apartment": "3",
            "is_default": default,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _order_from_menu(
    client,
    customer,
    *,
    menu_item_id: str,
    address_id: str,
    quantity: int = 1,
):
    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=customer["headers"],
        json={
            "daily_menu_item_id": menu_item_id,
            "quantity": quantity,
        },
    )
    assert cart.status_code == 201, cart.text
    order = client.post(
        "/api/v1/customer/orders",
        headers=customer["headers"],
        json={
            "cart_id": cart.json()["id"],
            "delivery_address_id": address_id,
        },
    )
    return order


def _create_import(client, headers, *, reference: str, source_currency="EGP", amount=5000, fx=None):
    payload = {
        "provider": "cloud_vendor",
        "pilot_program_id": None,
        "area": None,
        "period_start": date.today().isoformat(),
        "period_end": date.today().isoformat(),
        "source_currency": source_currency,
        "fx_rate_to_egp": fx,
        "fx_reference": "documented-fx" if fx else None,
        "external_reference": reference,
        "lines": [
            {
                "line_key": "line-1",
                "order_id": None,
                "incurred_on": date.today().isoformat(),
                "cost_type": "cloud_infrastructure",
                "source_amount_minor": amount,
                "external_reference": f"{reference}-line",
                "raw_json": {"fixture": True},
            }
        ],
    }
    created = client.post(
        "/api/v1/admin/economics/imports",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    batch_id = created.json()["batch"]["id"]
    validated = client.post(
        f"/api/v1/admin/economics/imports/{batch_id}/validate",
        headers=headers,
    )
    assert validated.status_code == 200, validated.text
    return validated.json()


def _create_clean_settlement(client, headers, *, tx_id: str, reference: str):
    order_id, payment_id = _paymob_ledger(
        client,
        tx_id=tx_id,
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
            "external_reference": reference,
            "lines": [
                {
                    "provider_transaction_id": tx_id,
                    "settlement_reference": f"{reference}-line",
                    "gross_amount_minor": 30000,
                    "fee_minor": 750,
                    "refund_minor": 0,
                    "net_settlement_minor": 29250,
                    "is_settled": True,
                    "settled_at": utc_now().isoformat(),
                    "raw_json": {"fixture": True},
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
    assert reconciled.json()["batch"]["status"] == "reconciled"
    return reconciled.json(), UUID(payment_id.hex if hasattr(payment_id, "hex") else str(payment_id))


def test_customer_cannot_access_traffic_or_vendor_accounting(login):
    client = login["client"]
    assert client.get(
        "/api/v1/admin/traffic/zones",
        headers=login["headers"],
    ).status_code == 403
    assert client.get(
        "/api/v1/admin/vendor-accounting/summary",
        headers=login["headers"],
    ).status_code == 403


def test_selected_delivery_address_is_snapshotted_atomically_and_governed(login):
    client = login["client"]
    area = "Sprint48 Atomic Zone"
    zone_id, _ = _live_zone(area=area, daily_cap=5)

    default_address = _address(client, login, "6 أكتوبر", default=True)
    selected_address = _address(client, login, area, default=False)
    service_date = (date.today() + timedelta(days=1)).isoformat()
    menu = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=10,
    )

    order = _order_from_menu(
        client,
        login,
        menu_item_id=menu["id"],
        address_id=selected_address["id"],
    )
    assert order.status_code == 201, order.text

    with SessionLocal() as db:
        snapshot = db.get(
            OrderDeliveryAddressEntity,
            UUID(order.json()["id"]),
        )
        assert snapshot is not None
        assert snapshot.area == area
        assert snapshot.source_address_id == UUID(selected_address["id"])
        event = db.scalar(
            select(ZoneAdmissionEventEntity).where(
                ZoneAdmissionEventEntity.zone_id == zone_id,
                ZoneAdmissionEventEntity.order_id == UUID(order.json()["id"]),
            )
        )
        assert event is not None
        assert event.decision == "admitted"
        assert event.reason == "admitted"


def test_zone_daily_cap_rejects_second_checkout_and_persists_rejection(client):
    area = "Sprint48 Daily Cap"
    zone_id, _ = _live_zone(area=area, daily_cap=1)
    service_date = (date.today() + timedelta(days=2)).isoformat()
    menu = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=20,
    )

    customer1 = login_phone(client, "01048000001")
    customer2 = login_phone(client, "01048000002")
    address1 = _address(client, customer1, area, default=True)
    address2 = _address(client, customer2, area, default=True)

    first = _order_from_menu(
        client,
        customer1,
        menu_item_id=menu["id"],
        address_id=address1["id"],
    )
    assert first.status_code == 201, first.text

    second = _order_from_menu(
        client,
        customer2,
        menu_item_id=menu["id"],
        address_id=address2["id"],
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "expansion_capacity_unavailable"
    assert second.json()["error"]["details"]["reason"] == "zone_daily_cap_reached"

    with SessionLocal() as db:
        rejected = db.scalar(
            select(ZoneAdmissionEventEntity).where(
                ZoneAdmissionEventEntity.zone_id == zone_id,
                ZoneAdmissionEventEntity.customer_id
                == UUID(customer2["body"]["user"]["id"]),
                ZoneAdmissionEventEntity.decision == "rejected",
            )
        )
        assert rejected is not None
        assert rejected.reason == "zone_daily_cap_reached"
        assert rejected.order_id is None


def test_rollout_bucket_is_deterministic_and_blocks_outside_canary(client):
    area = "Sprint48 Canary Bucket"
    zone_id, _ = _live_zone(
        area=area,
        daily_cap=20,
        rollout_stage="canary",
        rollout_percent=10,
        enforce_bucket=True,
    )
    zone_uuid = UUID(str(zone_id))

    chosen = None
    for i in range(1, 20):
        customer = login_phone(client, f"0104810{i:04d}")
        customer_id = UUID(customer["body"]["user"]["id"])
        bucket = LaunchTrafficGovernanceService.rollout_bucket(
            zone_uuid,
            customer_id,
        )
        if bucket >= 10:
            chosen = (customer, bucket)
            break
    assert chosen is not None
    customer, bucket = chosen

    service_date = (date.today() + timedelta(days=3)).isoformat()
    menu = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=10,
    )
    address = _address(client, customer, area, default=True)

    response = _order_from_menu(
        client,
        customer,
        menu_item_id=menu["id"],
        address_id=address["id"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "outside_rollout_bucket"

    with SessionLocal() as db:
        event = db.scalar(
            select(ZoneAdmissionEventEntity).where(
                ZoneAdmissionEventEntity.zone_id == zone_uuid,
                ZoneAdmissionEventEntity.customer_id
                == UUID(customer["body"]["user"]["id"]),
            )
        )
        assert event.rollout_bucket == bucket
        assert event.rollout_percent == 10


def test_hourly_and_chef_caps_are_enforced_via_policy(client):
    area = "Sprint48 Hourly Chef Cap"
    zone_id, _ = _live_zone(
        area=area,
        daily_cap=20,
        hourly_cap=1,
        chef_cap=20,
    )
    service_date = (date.today() + timedelta(days=4)).isoformat()
    menu = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=20,
    )
    c1 = login_phone(client, "01048200001")
    c2 = login_phone(client, "01048200002")
    a1 = _address(client, c1, area, default=True)
    a2 = _address(client, c2, area, default=True)

    assert _order_from_menu(
        client, c1, menu_item_id=menu["id"], address_id=a1["id"]
    ).status_code == 201

    blocked = _order_from_menu(
        client, c2, menu_item_id=menu["id"], address_id=a2["id"]
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["details"]["reason"] == "zone_hourly_cap_reached"

    headers, _ = admin_headers()
    update = client.patch(
        f"/api/v1/admin/traffic/zones/{zone_id}/caps",
        headers=headers,
        json={"hourly_order_cap": 20, "chef_daily_order_cap": 1},
    )
    assert update.status_code == 200
    assert update.json()["daily_order_cap"] == 20
    assert update.json()["hourly_order_cap"] == 20
    assert update.json()["chef_daily_order_cap"] == 1

    c3 = login_phone(client, "01048200003")
    a3 = _address(client, c3, area, default=True)
    chef_blocked = _order_from_menu(
        client, c3, menu_item_id=menu["id"], address_id=a3["id"]
    )
    assert chef_blocked.status_code == 409
    assert chef_blocked.json()["error"]["details"]["reason"] == "chef_daily_cap_reached"


def test_delivery_address_change_cannot_bypass_full_zone(client):
    area = "Sprint48 Address Change Zone"
    _live_zone(area=area, daily_cap=1)
    service_date = (date.today() + timedelta(days=5)).isoformat()
    menu = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=20,
    )

    c1 = login_phone(client, "01048300001")
    z1 = _address(client, c1, area, default=True)
    first = _order_from_menu(
        client, c1, menu_item_id=menu["id"], address_id=z1["id"]
    )
    assert first.status_code == 201

    c2 = login_phone(client, "01048300002")
    outside = _address(client, c2, "6 أكتوبر", default=True)
    inside = _address(client, c2, area, default=False)
    second = _order_from_menu(
        client, c2, menu_item_id=menu["id"], address_id=outside["id"]
    )
    assert second.status_code == 201

    change = client.put(
        f"/api/v1/customer/orders/{second.json()['id']}/delivery-address",
        headers=c2["headers"],
        json={"address_id": inside["id"]},
    )
    assert change.status_code == 409
    assert change.json()["error"]["details"]["reason"] == "zone_daily_cap_reached"

    with SessionLocal() as db:
        snapshot = db.get(
            OrderDeliveryAddressEntity,
            UUID(second.json()["id"]),
        )
        assert snapshot.area == "6 أكتوبر"


def test_monitoring_snapshot_and_control_room_detect_red_capacity(client):
    area = "Sprint48 Monitoring"
    zone_id, _ = _live_zone(
        area=area,
        daily_cap=1,
        hourly_cap=10,
        chef_cap=10,
    )
    service_date = (date.today() + timedelta(days=6)).isoformat()
    menu = publish_today_item(
        client,
        CHEF_1_ID,
        CHEF_1_PHONE,
        service_date,
        quantity=20,
    )
    c1 = login_phone(client, "01048400001")
    c2 = login_phone(client, "01048400002")
    a1 = _address(client, c1, area, default=True)
    a2 = _address(client, c2, area, default=True)
    assert _order_from_menu(client,c1,menu_item_id=menu["id"],address_id=a1["id"]).status_code == 201
    assert _order_from_menu(client,c2,menu_item_id=menu["id"],address_id=a2["id"]).status_code == 409

    headers, _ = admin_headers()
    snapshot = client.post(
        f"/api/v1/admin/traffic/zones/{zone_id}/monitoring/refresh",
        headers=headers,
        params={"service_date": service_date},
    )
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert body["admitted_orders_today"] == 1
    assert body["daily_utilization_pct"] == 100.0
    assert body["admission_attempts_last_hour"] >= 2
    assert body["admission_rejections_last_hour"] >= 1
    assert body["health"] == "red"
    assert "daily_capacity_critical" in body["blockers_json"]

    refreshed = client.post(
        "/api/v1/admin/control-room/incidents/refresh",
        headers=headers,
    )
    assert refreshed.status_code == 200
    incidents = client.get(
        "/api/v1/admin/control-room/incidents",
        headers=headers,
        params={"category": "traffic"},
    )
    assert incidents.status_code == 200
    assert any(
        x["source_id"] == str(zone_id)
        and x["severity"] == "critical"
        for x in incidents.json()
    )


def test_expansion_monitor_is_worker_maintenance_job(client):
    with SessionLocal() as db:
        jobs = BackgroundJobService(
            db,
            get_settings(),
        ).schedule_maintenance()
        assert any(x.job_type == "expansion.monitor" for x in jobs)
        assert len(jobs) == 13


def test_provider_import_risk_flags_and_maker_checker_apply(client):
    headers1, admin1 = admin_headers()
    headers2, admin2 = admin_headers()

    settings = get_settings()
    old_dual = settings.vendor_accounting_require_dual_control
    settings.vendor_accounting_require_dual_control = True
    try:
        validated = _create_import(
            client,
            headers1,
            reference="s48-maker-checker-import",
            source_currency="USD",
            amount=20000,
            fx=50,
        )
        batch = validated["batch"]
        assert batch["status"] == "validated"
        assert "foreign_currency" in batch["risk_flags_json"]
        assert "high_value_import" in batch["risk_flags_json"]
        assert "unscoped_pilot_program" in batch["risk_flags_json"]

        same_admin = client.post(
            f"/api/v1/admin/vendor-accounting/imports/{batch['id']}/approve",
            headers=headers1,
            json={"note": "Creator must not approve."},
        )
        assert same_admin.status_code == 409
        assert same_admin.json()["error"]["code"] == "vendor_accounting_dual_control_required"

        approved = client.post(
            f"/api/v1/admin/vendor-accounting/imports/{batch['id']}/approve",
            headers=headers2,
            json={"note": "Independent accounting review passed."},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["review_status"] == "approved"
        assert approved.json()["reviewed_by_admin_id"] == str(admin2)

        applied = client.post(
            f"/api/v1/admin/economics/imports/{batch['id']}/apply",
            headers=headers1,
        )
        assert applied.status_code == 200, applied.text
        assert applied.json()["batch"]["status"] == "applied"
    finally:
        settings.vendor_accounting_require_dual_control = old_dual

    with SessionLocal() as db:
        cost = db.scalar(
            select(EconomicsCostEntryEntity).where(
                EconomicsCostEntryEntity.external_reference.like(
                    "provider-import:cloud_vendor:s48-maker-checker-import:%"
                )
            )
        )
        assert cost is not None
        assert cost.is_verified is True


def test_strict_apply_requires_approved_import_review(client):
    headers, _ = admin_headers()
    settings = get_settings()
    old_dual = settings.vendor_accounting_require_dual_control
    settings.vendor_accounting_require_dual_control = True
    try:
        validated = _create_import(
            client,
            headers,
            reference="s48-review-required",
        )
        response = client.post(
            f"/api/v1/admin/economics/imports/{validated['batch']['id']}/apply",
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "provider_import_review_required"
    finally:
        settings.vendor_accounting_require_dual_control = old_dual


def test_import_review_reject_queue_and_summary(client):
    headers, _ = admin_headers()
    validated = _create_import(
        client,
        headers,
        reference="s48-reject-import",
    )
    rejected = client.post(
        f"/api/v1/admin/vendor-accounting/imports/{validated['batch']['id']}/reject",
        headers=headers,
        json={"note": "Invoice evidence is incomplete."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"

    queue = client.get(
        "/api/v1/admin/vendor-accounting/import-reviews",
        headers=headers,
        params={"review_status": "rejected"},
    )
    assert queue.status_code == 200
    assert any(x["id"] == validated["batch"]["id"] for x in queue.json())

    summary = client.get(
        "/api/v1/admin/vendor-accounting/summary",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["imports_rejected"] >= 1


def test_clean_settlement_moves_to_review_then_closes_with_independent_admin(client):
    headers1, _ = admin_headers()
    headers2, _ = admin_headers()
    settings = get_settings()
    old_dual = settings.vendor_accounting_require_dual_control
    settings.vendor_accounting_require_dual_control = True
    try:
        reconciled, _ = _create_clean_settlement(
            client,
            headers1,
            tx_id="s48-settlement-close",
            reference="s48-settlement-close-ref",
        )
        batch = reconciled["batch"]
        assert batch["operations_status"] == "review"

        creator_close = client.post(
            f"/api/v1/admin/vendor-accounting/settlements/{batch['id']}/close",
            headers=headers1,
            json={"note": "Creator trying to close."},
        )
        assert creator_close.status_code == 409

        closed = client.post(
            f"/api/v1/admin/vendor-accounting/settlements/{batch['id']}/close",
            headers=headers2,
            json={"note": "Independent settlement close evidence checked."},
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["operations_status"] == "closed"
        assert closed.json()["closed_at"] is not None

        reopened = client.post(
            f"/api/v1/admin/vendor-accounting/settlements/{batch['id']}/reopen",
            headers=headers2,
            json={"note": "Reopen due to new provider evidence."},
        )
        assert reopened.status_code == 200
        assert reopened.json()["operations_status"] == "reopened"
        assert reopened.json()["closed_at"] is None
    finally:
        settings.vendor_accounting_require_dual_control = old_dual


def test_settlement_close_blocks_open_payment_reconciliation_issue(client):
    headers, _ = admin_headers()
    reconciled, payment_id = _create_clean_settlement(
        client,
        headers,
        tx_id="s48-settlement-open-issue",
        reference="s48-settlement-open-issue-ref",
    )
    batch_id = reconciled["batch"]["id"]

    with SessionLocal() as db:
        db.add(
            PaymentReconciliationIssueEntity(
                fingerprint="s48-settlement-open-issue-fingerprint",
                payment_id=payment_id,
                provider_transaction_id="s48-settlement-open-issue",
                issue_type="status_mismatch",
                status="open",
                expected_json={"status": "succeeded"},
                actual_json={"fixture": "open"},
                detected_at=utc_now(),
                last_detected_at=utc_now(),
            )
        )
        db.commit()

    close = client.post(
        f"/api/v1/admin/vendor-accounting/settlements/{batch_id}/close",
        headers=headers,
        json={"note": "Should be blocked by payment issue."},
    )
    assert close.status_code == 409
    assert close.json()["error"]["code"] == "settlement_payment_reconciliation_open"


def test_rollout_strict_mode_blocks_unclosed_source_settlement(client):
    headers, program, zone = _approved_zone(
        client,
        "Sprint48 Closed Settlement Gate",
    )
    _fund_required_budgets(client, headers, zone["id"])

    with SessionLocal() as db:
        batch = ProviderSettlementBatchEntity(
            provider="paymob",
            pilot_program_id=UUID(program["id"]),
            period_start=date.today(),
            period_end=date.today(),
            currency="EGP",
            external_reference="s48-unclosed-source-settlement",
            checksum_sha256="b" * 64,
            status="reconciled",
            operations_status="review",
            rows_count=0,
            matched_lines=0,
            mismatched_lines=0,
            gross_minor=0,
            fees_minor=0,
            refunds_minor=0,
            net_settlement_minor=0,
            blockers_json=[],
        )
        db.add(batch)
        db.commit()
        batch_id = batch.id

    settings = get_settings()
    old = settings.vendor_accounting_require_closed_settlements_for_rollout
    settings.vendor_accounting_require_closed_settlements_for_rollout = True
    try:
        blocked = client.post(
            f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
            headers=headers,
            json={"daily_order_cap": 10},
        )
        assert blocked.status_code == 409
        assert (
            "unclosed_provider_settlement_batches"
            in blocked.json()["error"]["details"]["blockers"]
        )

        closed = client.post(
            f"/api/v1/admin/vendor-accounting/settlements/{batch_id}/close",
            headers=headers,
            json={"note": "Zero-row fixture closed for strict gate test."},
        )
        assert closed.status_code == 200, closed.text

        started = client.post(
            f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
            headers=headers,
            json={"daily_order_cap": 10},
        )
        assert started.status_code == 200, started.text
        assert started.json()["rollout_stage"] == "canary"
    finally:
        settings.vendor_accounting_require_closed_settlements_for_rollout = old


def test_vendor_accounting_queue_contracts_are_admin_visible(client):
    headers, _ = admin_headers()
    summary = client.get(
        "/api/v1/admin/vendor-accounting/summary",
        headers=headers,
    )
    imports = client.get(
        "/api/v1/admin/vendor-accounting/import-reviews",
        headers=headers,
    )
    settlements = client.get(
        "/api/v1/admin/vendor-accounting/settlements",
        headers=headers,
    )
    assert summary.status_code == 200
    assert imports.status_code == 200
    assert settlements.status_code == 200
    for key in [
        "imports_pending_review",
        "imports_high_risk_open",
        "settlements_in_review",
        "settlements_closed",
        "settlements_blocked",
    ]:
        assert key in summary.json()



def test_production_rejects_disabled_sprint48_fail_closed_controls():
    import pytest

    with pytest.raises(ValueError) as exc:
        Settings(
            env="production",
            database_url="postgresql+psycopg://baytna:strong@db:5432/baytna",
            cors_origins="https://app.baytna.example",
            allowed_hosts="api.baytna.example",
            security_hsts_enabled=True,
            dev_return_otp=False,
            seed_demo_data=False,
            payment_provider="real_provider",
            jwt_secret="J" * 48,
            otp_pepper="O" * 48,
            refresh_token_pepper="R" * 48,
            payment_webhook_secret="P" * 48,
            storage_provider="s3",
            storage_bucket="baytna-production",
            media_signing_secret="M" * 48,
            integration_encryption_secret="I" * 48,
            notification_provider_webhook_secret="W" * 48,
            notification_push_provider="http",
            notification_push_endpoint="https://push.example.com/send",
            notification_sms_provider="http",
            notification_sms_endpoint="https://sms.example.com/send",
            expansion_rollout_required=False,
            traffic_require_delivery_address_for_checkout=False,
            vendor_accounting_require_dual_control=False,
            vendor_accounting_require_closed_settlements_for_rollout=False,
        )

    text = str(exc.value)
    assert "BAYTNA_EXPANSION_ROLLOUT_REQUIRED must be true" in text
    assert "BAYTNA_TRAFFIC_REQUIRE_DELIVERY_ADDRESS_FOR_CHECKOUT must be true" in text
    assert "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_DUAL_CONTROL must be true" in text
    assert (
        "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_CLOSED_SETTLEMENTS_FOR_ROLLOUT must be true"
        in text
    )
