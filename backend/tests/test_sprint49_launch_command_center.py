from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    DailyFinancialCloseEntity,
    EconomicsCostEntryEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionZoneEntity,
    LaunchCommandEventEntity,
    LaunchCommandSessionEntity,
    LaunchEvidencePackEntity,
    LaunchRollbackDrillEntity,
    LaunchTrafficOverrideEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    PaymentEntity,
    PilotProgramEntity,
    ProviderCostImportBatchEntity,
    ProviderSettlementBatchEntity,
    UserEntity,
    ZoneTrafficPolicyEntity,
)
from app.core.security import create_access_token, utc_now
from app.core.models import UserRole
from app.modules.launch_command.service import LaunchCommandService
from app.modules.reliability.jobs import BackgroundJobService
from tests.test_admin_operations import admin_headers
from tests.test_sprint47_financial_automation import (
    _approved_zone,
    _fund_required_budgets,
)


def _admin():
    return admin_headers()


def _basic_program_zone(*, area: str, status: str = "approved", rollout_stage: str = "not_started"):
    with SessionLocal() as db:
        program = PilotProgramEntity(
            name=f"Sprint49 {area}",
            area=area,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            status="active",
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
            status=status,
            min_delivered_orders=1,
            min_contribution_margin_pct=0,
            min_operational_profit_minor=1,
            rollout_stage=rollout_stage,
            rollout_percent=10 if rollout_stage == "canary" else 0,
            daily_order_cap=10,
        )
        db.add(zone)
        db.flush()
        db.add(
            ZoneTrafficPolicyEntity(
                zone_id=zone.id,
                is_enabled=True,
                hourly_order_cap=8,
                chef_daily_order_cap=12,
                enforce_rollout_bucket=True,
                warning_utilization_pct=80,
                critical_utilization_pct=95,
                rejection_spike_pct=30,
                rejection_spike_min_attempts=5,
                note="Sprint49 fixture",
            )
        )
        db.commit()
        return program.id, zone.id


def _session_payload(program_id, zone_id, admin1, admin2=None):
    return {
        "pilot_program_id": str(program_id),
        "zone_id": str(zone_id),
        "launch_date": date.today().isoformat(),
        "incident_commander_admin_id": str(admin1),
        "finance_admin_id": str(admin2) if admin2 else None,
        "operations_admin_id": str(admin2) if admin2 else None,
        "notes": "Sprint49 command-center fixture",
    }


def _create_active_session(client, *, program_id, zone_id, headers, admin1, admin2=None):
    created = client.post(
        "/api/v1/admin/launch-command/sessions",
        headers=headers,
        json=_session_payload(program_id, zone_id, admin1, admin2),
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    started = client.post(
        f"/api/v1/admin/launch-command/sessions/{session_id}/start",
        headers=headers,
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "active"
    return session_id


def _seed_ready_daily_finance(program_id: UUID, zone_id: UUID, day: date):
    with SessionLocal() as db:
        # Customer for one delivered service-day order.
        customer = UserEntity(
            phone=f"+2010{uuid4().int % 100000000:08d}",
            role="customer",
            is_active=True,
        )
        db.add(customer)
        db.flush()

        chef_id = UUID("10000000-0000-0000-0000-000000000001")
        order = OrderEntity(
            customer_id=customer.id,
            chef_id=chef_id,
            source_cart_id=None,
            service_date=day,
            status="delivered",
            subtotal_minor=30000,
            delivery_fee_minor=0,
            discount_minor=0,
            total_minor=30000,
            currency="EGP",
        )
        db.add(order)
        db.flush()
        db.add(
            OrderDeliveryAddressEntity(
                order_id=order.id,
                source_address_id=None,
                label="launch",
                area=db.get(ExpansionZoneEntity, zone_id).area,
                street="x",
                building="1",
                floor="1",
                apartment="1",
            )
        )
        payment = PaymentEntity(
            order_id=order.id,
            customer_id=customer.id,
            provider="mock",
            provider_reference=f"s49-{order.id}",
            idempotency_key=f"s49-{order.id}",
            amount_minor=30000,
            refunded_minor=0,
            currency="EGP",
            status="succeeded",
            expires_at=utc_now() + timedelta(hours=1),
            succeeded_at=utc_now(),
        )
        db.add(payment)

        for kind, amount in [
            ("chef_payout", 18000),
            ("delivery_partner", 3000),
            ("payment_processing", 600),
        ]:
            db.add(
                EconomicsCostEntryEntity(
                    pilot_program_id=program_id,
                    order_id=order.id,
                    area=db.get(ExpansionZoneEntity, zone_id).area,
                    incurred_on=day,
                    cost_type=kind,
                    cost_scope="variable",
                    amount_minor=amount,
                    currency="EGP",
                    source="manual",
                    external_reference=f"s49:{order.id}:{kind}",
                    is_verified=True,
                    verified_at=utc_now(),
                )
            )
        db.commit()
        return order.id


def test_customer_cannot_access_launch_command(login):
    response = login["client"].get(
        "/api/v1/admin/launch-command/sessions",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_create_session_seeds_twelve_required_runbook_steps(client):
    h1, admin1 = _admin()
    h2, admin2 = _admin()
    program_id, zone_id = _basic_program_zone(area="Sprint49 Runbook")

    created = client.post(
        "/api/v1/admin/launch-command/sessions",
        headers=h1,
        json=_session_payload(program_id, zone_id, admin1, admin2),
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]

    steps = client.get(
        f"/api/v1/admin/launch-command/sessions/{session_id}/runbook",
        headers=h1,
    )
    assert steps.status_code == 200
    assert len(steps.json()) == 12
    assert all(x["is_required"] for x in steps.json())
    assert all(x["status"] == "pending" for x in steps.json())


def test_only_one_open_session_per_zone(client):
    h1, admin1 = _admin()
    program_id, zone_id = _basic_program_zone(area="Sprint49 One Session")
    first = client.post(
        "/api/v1/admin/launch-command/sessions",
        headers=h1,
        json=_session_payload(program_id, zone_id, admin1),
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/admin/launch-command/sessions",
        headers=h1,
        json=_session_payload(program_id, zone_id, admin1),
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "launch_session_already_open"


def test_strict_rollout_requires_active_launch_command_session(client):
    headers, program, zone = _approved_zone(client, "Sprint49 Command Gate")
    _fund_required_budgets(client, headers, zone["id"])
    settings = get_settings()
    old = settings.launch_command_required
    settings.launch_command_required = True
    try:
        blocked = client.post(
            f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
            headers=headers,
            json={"daily_order_cap": 10},
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "launch_command_session_required"

        admin_id = UUID(
            client.get("/api/v1/admin/profile", headers=headers).json()["id"]
        )
        created = client.post(
            "/api/v1/admin/launch-command/sessions",
            headers=headers,
            json=_session_payload(
                UUID(program["id"]),
                UUID(zone["id"]),
                admin_id,
            ),
        )
        assert created.status_code == 201, created.text
        sid = created.json()["id"]
        assert client.post(
            f"/api/v1/admin/launch-command/sessions/{sid}/start",
            headers=headers,
        ).status_code == 200

        started = client.post(
            f"/api/v1/admin/economics/zones/{zone['id']}/rollout/start",
            headers=headers,
            json={"daily_order_cap": 10},
        )
        assert started.status_code == 200, started.text
        assert started.json()["rollout_stage"] == "canary"
    finally:
        settings.launch_command_required = old


def test_emergency_cap_override_only_reduces_and_reverts(client):
    h1, admin1 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Override",
        status="live",
        rollout_stage="canary",
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
    )

    too_high = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/traffic-overrides",
        headers=h1,
        json={
            "override_type": "daily_order_cap",
            "value": 20,
            "duration_minutes": 30,
            "reason": "Should not increase launch traffic",
        },
    )
    assert too_high.status_code == 409
    assert too_high.json()["error"]["code"] == "launch_override_cannot_increase_traffic"

    created = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/traffic-overrides",
        headers=h1,
        json={
            "override_type": "daily_order_cap",
            "value": 4,
            "duration_minutes": 30,
            "reason": "Courier capacity temporarily reduced",
        },
    )
    assert created.status_code == 201, created.text
    override_id = created.json()["id"]

    with SessionLocal() as db:
        assert db.get(ExpansionZoneEntity, zone_id).daily_order_cap == 4

    reverted = client.post(
        f"/api/v1/admin/launch-command/traffic-overrides/{override_id}/revert",
        headers=h1,
    )
    assert reverted.status_code == 200
    assert reverted.json()["status"] == "reverted"
    with SessionLocal() as db:
        assert db.get(ExpansionZoneEntity, zone_id).daily_order_cap == 10


def test_admission_stop_override_is_auto_expired_and_restored(client):
    h1, admin1 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Expiry",
        status="live",
        rollout_stage="canary",
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
    )
    created = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/traffic-overrides",
        headers=h1,
        json={
            "override_type": "admission_enabled",
            "value": False,
            "duration_minutes": 30,
            "reason": "Emergency stop drill",
        },
    )
    assert created.status_code == 201
    oid = UUID(created.json()["id"])

    with SessionLocal() as db:
        assert db.get(ZoneTrafficPolicyEntity, zone_id).is_enabled is False
        row = db.get(LaunchTrafficOverrideEntity, oid)
        row.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    with SessionLocal() as db:
        result = LaunchCommandService(db, get_settings()).maintain()
        assert result["expired_overrides"] == 1

    with SessionLocal() as db:
        assert db.get(ZoneTrafficPolicyEntity, zone_id).is_enabled is True
        assert db.get(LaunchTrafficOverrideEntity, oid).status == "expired"


def test_daily_financial_close_ready_then_independent_close(client):
    h1, admin1 = _admin()
    h2, admin2 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Daily Close",
        status="live",
        rollout_stage="canary",
    )
    _seed_ready_daily_finance(program_id, zone_id, date.today())
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )

    prepared = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/financial-closes/prepare",
        headers=h1,
        json={"close_date": date.today().isoformat(), "note": "Prepare launch day"},
    )
    assert prepared.status_code == 200, prepared.text
    body = prepared.json()
    assert body["status"] == "ready"
    assert body["revenue_coverage_pct"] == 100.0
    assert body["cost_coverage_pct"] == 100.0
    close_id = body["id"]

    settings = get_settings()
    old = settings.launch_command_require_dual_control
    settings.launch_command_require_dual_control = True
    try:
        same = client.post(
            f"/api/v1/admin/launch-command/financial-closes/{close_id}/close",
            headers=h1,
            json={"note": "same admin should be blocked"},
        )
        assert same.status_code == 409
        assert same.json()["error"]["code"] == "launch_dual_control_required"

        closed = client.post(
            f"/api/v1/admin/launch-command/financial-closes/{close_id}/close",
            headers=h2,
            json={"note": "Independent finance close verified"},
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == "closed"
        assert len(closed.json()["checksum_sha256"]) == 64
        assert closed.json()["closed_by_admin_id"] == str(admin2)
    finally:
        settings.launch_command_require_dual_control = old


def test_daily_close_blocks_unverified_cost(client):
    h1, admin1 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Blocked Close",
        status="live",
        rollout_stage="canary",
    )
    with SessionLocal() as db:
        db.add(
            EconomicsCostEntryEntity(
                pilot_program_id=program_id,
                order_id=None,
                area="Sprint49 Blocked Close",
                incurred_on=date.today(),
                cost_type="fixed_operations",
                cost_scope="fixed",
                amount_minor=1000,
                currency="EGP",
                source="manual",
                external_reference=f"s49-unverified-{uuid4()}",
                is_verified=False,
            )
        )
        db.commit()
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
    )
    prepared = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/financial-closes/prepare",
        headers=h1,
        json={"close_date": date.today().isoformat()},
    )
    assert prepared.status_code == 200
    assert prepared.json()["status"] == "blocked"
    assert "unverified_cost_entries" in prepared.json()["blockers_json"]


def test_live_controlled_rollback_restores_admission_and_requires_independent_verifier(client):
    h1, admin1 = _admin()
    h2, admin2 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Rollback",
        status="live",
        rollout_stage="canary",
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )
    settings = get_settings()
    old = settings.launch_command_require_dual_control
    settings.launch_command_require_dual_control = True
    try:
        started = client.post(
            f"/api/v1/admin/launch-command/sessions/{sid}/rollback-drills",
            headers=h1,
            json={
                "mode": "live_controlled",
                "target_recovery_seconds": 300,
                "note": "Controlled admission stop",
            },
        )
        assert started.status_code == 201, started.text
        did = started.json()["id"]
        with SessionLocal() as db:
            assert db.get(ZoneTrafficPolicyEntity, zone_id).is_enabled is False

        same = client.post(
            f"/api/v1/admin/launch-command/rollback-drills/{did}/complete",
            headers=h1,
            json={
                "passed": True,
                "evidence_reference": "s49://rollback/same-admin",
            },
        )
        assert same.status_code == 409

        completed = client.post(
            f"/api/v1/admin/launch-command/rollback-drills/{did}/complete",
            headers=h2,
            json={
                "passed": True,
                "evidence_reference": "s49://rollback/verified",
                "note": "Admission recovered",
            },
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "passed"
        with SessionLocal() as db:
            assert db.get(ZoneTrafficPolicyEntity, zone_id).is_enabled is True
    finally:
        settings.launch_command_require_dual_control = old


def test_worker_auto_recovers_timed_out_live_drill(client):
    h1, admin1 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Drill Timeout",
        status="live",
        rollout_stage="canary",
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
    )
    started = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/rollback-drills",
        headers=h1,
        json={"mode": "live_controlled", "target_recovery_seconds": 1},
    )
    assert started.status_code == 201
    did = UUID(started.json()["id"])
    with SessionLocal() as db:
        row = db.get(LaunchRollbackDrillEntity, did)
        row.started_at = utc_now() - timedelta(seconds=3)
        db.commit()
    with SessionLocal() as db:
        result = LaunchCommandService(db, get_settings()).maintain()
        assert result["auto_recovered_drills"] == 1
    with SessionLocal() as db:
        assert db.get(LaunchRollbackDrillEntity, did).status == "aborted"
        assert db.get(ZoneTrafficPolicyEntity, zone_id).is_enabled is True


def test_evidence_pack_is_incomplete_until_command_evidence_exists(client):
    h1, admin1 = _admin()
    h2, admin2 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Incomplete Evidence",
        status="live",
        rollout_stage="canary",
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )
    pack = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/evidence-packs",
        headers=h1,
    )
    assert pack.status_code == 201
    assert pack.json()["status"] == "incomplete"
    assert "required_runbook_steps_not_passed" in pack.json()["blockers_json"]
    assert "launch_day_financial_close_not_closed" in pack.json()["blockers_json"]
    assert "rollback_drill_not_passed" in pack.json()["blockers_json"]


def test_complete_evidence_pack_can_close_command_session(client):
    h1, admin1 = _admin()
    h2, admin2 = _admin()
    program_id, zone_id = _basic_program_zone(
        area="Sprint49 Complete Evidence",
        status="live",
        rollout_stage="canary",
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )

    # Required runbook evidence.
    steps = client.get(
        f"/api/v1/admin/launch-command/sessions/{sid}/runbook",
        headers=h1,
    ).json()
    for step in steps:
        passed = client.post(
            f"/api/v1/admin/launch-command/sessions/{sid}/runbook/{step['step_key']}",
            headers=h1,
            json={
                "status": "passed",
                "evidence_reference": f"s49://runbook/{step['step_key']}",
                "note": "Verified fixture",
            },
        )
        assert passed.status_code == 200, passed.text

    # Green monitoring.
    with SessionLocal() as db:
        db.add(
            ExpansionMonitoringSnapshotEntity(
                zone_id=zone_id,
                service_date=date.today(),
                rollout_stage="canary",
                rollout_percent=10,
                zone_daily_cap=10,
                admitted_orders_today=1,
                daily_utilization_pct=10,
                hourly_cap=8,
                admitted_orders_last_hour=1,
                hourly_utilization_pct=12.5,
                admission_attempts_last_hour=1,
                admission_rejections_last_hour=0,
                rejection_rate_pct=0,
                available_drivers=2,
                open_chefs=2,
                top_chef_orders=1,
                chef_daily_cap=12,
                top_chef_utilization_pct=8.33,
                health="green",
                blockers_json=[],
                generated_by="test",
            )
        )
        # Provider/accounting evidence required by pack.
        db.add(
            ProviderCostImportBatchEntity(
                provider="courier_partner",
                pilot_program_id=program_id,
                area="Sprint49 Complete Evidence",
                period_start=date.today(),
                period_end=date.today(),
                source_currency="EGP",
                fx_rate_to_egp=None,
                fx_reference=None,
                external_reference=f"s49-pack-import-{uuid4()}",
                checksum_sha256="a"*64,
                status="applied",
                rows_count=0,
                total_source_minor=0,
                total_egp_minor=0,
                applied_cost_entries=0,
                validation_errors_json=[],
                review_status="approved",
                reviewed_by_admin_id=admin2,
                review_note="fixture",
                risk_flags_json=[],
                reviewed_at=utc_now(),
                created_by_admin_id=admin1,
                validated_by_admin_id=admin1,
                applied_by_admin_id=admin1,
                validated_at=utc_now(),
                applied_at=utc_now(),
            )
        )
        db.add(
            ProviderSettlementBatchEntity(
                provider="paymob",
                pilot_program_id=program_id,
                period_start=date.today(),
                period_end=date.today(),
                currency="EGP",
                external_reference=f"s49-pack-settlement-{uuid4()}",
                checksum_sha256="b"*64,
                status="reconciled",
                operations_status="closed",
                rows_count=0,
                matched_lines=0,
                mismatched_lines=0,
                gross_minor=0,
                fees_minor=0,
                refunds_minor=0,
                net_settlement_minor=0,
                blockers_json=[],
                created_by_admin_id=admin1,
                reconciled_by_admin_id=admin1,
                closed_by_admin_id=admin2,
                reconciled_at=utc_now(),
                closed_at=utc_now(),
                close_note="fixture",
            )
        )
        db.commit()

    # Zero-activity financial close is allowed if there are no reconciliation blockers.
    prepared = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/financial-closes/prepare",
        headers=h1,
        json={"close_date": date.today().isoformat()},
    )
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == "ready"
    closed = client.post(
        f"/api/v1/admin/launch-command/financial-closes/{prepared.json()['id']}/close",
        headers=h2,
        json={"note": "Independent close"},
    )
    assert closed.status_code == 200, closed.text

    # Tabletop drill verified independently.
    drill = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/rollback-drills",
        headers=h1,
        json={"mode": "tabletop", "target_recovery_seconds": 300},
    )
    assert drill.status_code == 201
    done = client.post(
        f"/api/v1/admin/launch-command/rollback-drills/{drill.json()['id']}/complete",
        headers=h2,
        json={
            "passed": True,
            "evidence_reference": "s49://rollback/complete-pack",
        },
    )
    assert done.status_code == 200
    assert done.json()["status"] == "passed"

    pack = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/evidence-packs",
        headers=h1,
    )
    assert pack.status_code == 201, pack.text
    assert pack.json()["status"] == "complete", pack.json()["blockers_json"]
    assert pack.json()["blockers_json"] == []
    assert len(pack.json()["checksum_sha256"]) == 64

    completed = client.post(
        f"/api/v1/admin/launch-command/sessions/{sid}/complete",
        headers=h1,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_command_maintenance_is_worker_job_and_total_is_thirteen(client):
    with SessionLocal() as db:
        jobs = BackgroundJobService(db, get_settings()).schedule_maintenance()
        assert any(x.job_type == "launch.command.maintain" for x in jobs)
        assert len(jobs) == 13


def test_production_requires_sprint49_command_controls():
    with pytest.raises(ValueError) as exc:
        Settings(
            env="production",
            database_url="postgresql+psycopg://baytna:strong@db:5432/baytna",
            cors_origins="https://app.baytna.example",
            allowed_hosts="api.baytna.example",
            security_hsts_enabled=True,
            expansion_rollout_required=True,
            traffic_require_delivery_address_for_checkout=True,
            vendor_accounting_require_dual_control=True,
            vendor_accounting_require_closed_settlements_for_rollout=True,
            launch_command_required=False,
            launch_command_require_dual_control=False,
            dev_return_otp=False,
            seed_demo_data=False,
            payment_provider="real_provider",
            jwt_secret="J"*48,
            otp_pepper="O"*48,
            refresh_token_pepper="R"*48,
            payment_webhook_secret="P"*48,
            storage_provider="s3",
            storage_bucket="baytna-production",
            media_signing_secret="M"*48,
            integration_encryption_secret="I"*48,
            notification_provider_webhook_secret="W"*48,
            notification_push_provider="http",
            notification_push_endpoint="https://push.example.com/send",
            notification_sms_provider="http",
            notification_sms_endpoint="https://sms.example.com/send",
        )
    text = str(exc.value)
    assert "BAYTNA_LAUNCH_COMMAND_REQUIRED must be true" in text
    assert "BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL must be true" in text
