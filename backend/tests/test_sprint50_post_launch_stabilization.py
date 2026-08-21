from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    DailyFinancialCloseEntity,
    ExpansionCapacityForecastEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionReviewEntity,
    ExpansionRolloutEventEntity,
    ExpansionZoneEntity,
    LaunchCommandEventEntity,
    LaunchEvidencePackEntity,
    ZoneTrafficPolicyEntity,
)
from app.core.security import utc_now
from app.modules.launch_command.schemas import FinancialCloseActionRequest
from app.modules.launch_command.service import LaunchCommandService
from app.modules.launch_governance.service import LaunchTrafficGovernanceService
from app.modules.post_launch.service import PostLaunchStabilizationService
from app.modules.reliability.jobs import BackgroundJobService
from tests.test_admin_operations import admin_headers
from tests.test_sprint49_launch_command_center import (
    _basic_program_zone,
    _create_active_session,
)


def _enable_slo(zone_id, *, threshold=2):
    with SessionLocal() as db:
        policy = db.get(ZoneTrafficPolicyEntity, zone_id)
        policy.slo_auto_pause_enabled = True
        policy.slo_consecutive_red_snapshots = threshold
        db.commit()


def test_customer_cannot_access_sprint50_admin_apis(login):
    response = login["client"].get(
        "/api/v1/admin/post-launch/reviews",
        headers=login["headers"],
    )
    assert response.status_code == 403
    forecast = login["client"].get(
        f"/api/v1/admin/traffic/zones/{uuid4()}/capacity-forecasts",
        headers=login["headers"],
    )
    assert forecast.status_code == 403


def test_slo_policy_cannot_disable_anti_flapping_with_one_red_snapshot(client):
    headers, _ = admin_headers()
    _, zone_id = _basic_program_zone(area=f"Sprint50 Threshold {uuid4()}")
    response = client.put(
        f"/api/v1/admin/traffic/zones/{zone_id}/policy",
        headers=headers,
        json={
            "slo_auto_pause_enabled": True,
            "slo_consecutive_red_snapshots": 1,
        },
    )
    assert response.status_code == 422


def test_one_red_snapshot_does_not_pause_but_second_red_does(client):
    h1, admin1 = admin_headers()
    h2, admin2 = admin_headers()
    program_id, zone_id = _basic_program_zone(
        area=f"Sprint50 SLO {uuid4()}", status="live", rollout_stage="canary"
    )
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )
    _enable_slo(zone_id, threshold=2)

    with SessionLocal() as db:
        svc = LaunchTrafficGovernanceService(db, get_settings())
        first = svc.refresh_all_live_zones()
        assert first["health"]["red"] == 1
        assert first["auto_paused"] == 0
        zone = db.get(ExpansionZoneEntity, zone_id)
        assert zone.status == "live"

        second = svc.refresh_all_live_zones()
        assert second["auto_paused"] == 1
        db.expire_all()
        zone = db.get(ExpansionZoneEntity, zone_id)
        assert zone.status == "paused"
        assert zone.rollout_stage == "paused"

        events = list(
            db.scalars(
                select(ExpansionRolloutEventEntity).where(
                    ExpansionRolloutEventEntity.zone_id == zone_id,
                    ExpansionRolloutEventEntity.trigger_reason == "slo_auto_pause",
                )
            ).all()
        )
        assert len(events) == 1
        assert events[0].trigger_source == "system"
        assert events[0].trigger_evidence_json["red_streak"] >= 2

        command_event = db.scalar(
            select(LaunchCommandEventEntity).where(
                LaunchCommandEventEntity.session_id == UUID(sid),
                LaunchCommandEventEntity.event_type == "slo.auto_pause",
            )
        )
        assert command_event is not None


def test_red_streak_resets_on_non_red_snapshot(client):
    program_id, zone_id = _basic_program_zone(
        area=f"Sprint50 Reset {uuid4()}", status="live", rollout_stage="canary"
    )
    _enable_slo(zone_id, threshold=2)
    with SessionLocal() as db:
        svc = LaunchTrafficGovernanceService(db, get_settings())
        svc.refresh_all_live_zones()
        first = db.scalar(
            select(ExpansionMonitoringSnapshotEntity)
            .where(ExpansionMonitoringSnapshotEntity.zone_id == zone_id)
            .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
            .limit(1)
        )
        assert first.health == "red"
        # Durable non-red evidence must break the streak.
        first.health = "green"
        first.blockers_json = []
        db.commit()
        result = svc.refresh_all_live_zones()
        assert result["auto_paused"] == 0
        db.expire_all()
        assert db.get(ExpansionZoneEntity, zone_id).status == "live"


def test_worker_monitor_creates_one_capacity_forecast_per_snapshot(client):
    program_id, zone_id = _basic_program_zone(
        area=f"Sprint50 Forecast {uuid4()}", status="live", rollout_stage="canary"
    )
    with SessionLocal() as db:
        svc = LaunchTrafficGovernanceService(db, get_settings())
        result = svc.refresh_all_live_zones()
        assert sum(result["capacity_forecast_risk"].values()) == 1
        snapshot = db.scalar(
            select(ExpansionMonitoringSnapshotEntity)
            .where(ExpansionMonitoringSnapshotEntity.zone_id == zone_id)
            .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
            .limit(1)
        )
        forecasts = list(
            db.scalars(
                select(ExpansionCapacityForecastEntity).where(
                    ExpansionCapacityForecastEntity.zone_id == zone_id
                )
            ).all()
        )
        assert len(forecasts) == 1
        again = svc.capacity_forecast_for_snapshot(snapshot.id)
        assert again.id == forecasts[0].id
        assert len(
            list(
                db.scalars(
                    select(ExpansionCapacityForecastEntity).where(
                        ExpansionCapacityForecastEntity.zone_id == zone_id
                    )
                ).all()
            )
        ) == 1


def test_auto_pause_is_idempotent_and_never_auto_resumes(client):
    program_id, zone_id = _basic_program_zone(
        area=f"Sprint50 Idempotent {uuid4()}", status="live", rollout_stage="canary"
    )
    _enable_slo(zone_id, threshold=2)
    with SessionLocal() as db:
        svc = LaunchTrafficGovernanceService(db, get_settings())
        warmup = svc.refresh_all_live_zones()
        assert warmup["auto_paused"] == 0
        first = svc.refresh_all_live_zones()
        assert first["auto_paused"] == 1
        second = svc.refresh_all_live_zones()
        assert second["auto_paused"] == 0
        db.expire_all()
        zone = db.get(ExpansionZoneEntity, zone_id)
        assert zone.status == "paused"
        events = list(
            db.scalars(
                select(ExpansionRolloutEventEntity).where(
                    ExpansionRolloutEventEntity.zone_id == zone_id,
                    ExpansionRolloutEventEntity.trigger_reason == "slo_auto_pause",
                )
            ).all()
        )
        assert len(events) == 1


def test_daily_close_cadence_system_prepares_once_and_admin_can_close(client):
    h1, admin1 = admin_headers()
    h2, admin2 = admin_headers()
    program_id, zone_id = _basic_program_zone(area=f"Sprint50 Close {uuid4()}")
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )
    target_day = date.today() - timedelta(days=2)
    with SessionLocal() as db:
        session = db.get(__import__('app.core.db_models', fromlist=['LaunchCommandSessionEntity']).LaunchCommandSessionEntity, UUID(sid))
        session.launch_date = target_day
        db.commit()
        settings = get_settings().model_copy(
            update={
                "launch_daily_close_cadence_enabled": True,
                "launch_post_launch_stabilization_days": 7,
                "launch_financial_close_grace_hours": 1,
                "launch_command_require_dual_control": True,
            }
        )
        svc = LaunchCommandService(db, settings)
        created = svc.prepare_due_financial_closes()
        assert created >= 1
        assert svc.prepare_due_financial_closes() == 0
        row = db.scalar(
            select(DailyFinancialCloseEntity).where(
                DailyFinancialCloseEntity.session_id == UUID(sid),
                DailyFinancialCloseEntity.close_date == target_day,
            )
        )
        assert row is not None
        assert row.prepared_by_system is True
        assert row.prepared_by_admin_id is None
        assert row.cadence_due_at is not None
        assert row.status == "ready"

        closed = svc.close_financial_day(
            close_id=row.id,
            payload=FinancialCloseActionRequest(note="Independent finance close"),
            admin_id=admin2,
            request_id=None,
        )
        assert closed.status == "closed"
        assert closed.checksum_sha256


def test_incomplete_evidence_retention_prunes_only_superseded_working_pack(client):
    h1, admin1 = admin_headers()
    h2, admin2 = admin_headers()
    program_id, zone_id = _basic_program_zone(area=f"Sprint50 Retention {uuid4()}")
    sid = _create_active_session(
        client,
        program_id=program_id,
        zone_id=zone_id,
        headers=h1,
        admin1=admin1,
        admin2=admin2,
    )
    now = utc_now()
    with SessionLocal() as db:
        old = LaunchEvidencePackEntity(
            session_id=UUID(sid),
            status="incomplete",
            release_version="0.50.0",
            migration_head="0025_sprint50",
            evidence_json={"generation": 1},
            blockers_json=["x"],
            checksum_sha256="a" * 64,
            retention_class="working",
            retain_until=now - timedelta(days=1),
            generated_by_admin_id=admin1,
            generated_at=now - timedelta(days=40),
        )
        newest = LaunchEvidencePackEntity(
            session_id=UUID(sid),
            status="incomplete",
            release_version="0.50.0",
            migration_head="0025_sprint50",
            evidence_json={"generation": 2},
            blockers_json=["y"],
            checksum_sha256="b" * 64,
            retention_class="working",
            retain_until=now - timedelta(days=1),
            generated_by_admin_id=admin1,
            generated_at=now - timedelta(days=35),
        )
        final = LaunchEvidencePackEntity(
            session_id=UUID(sid),
            status="complete",
            release_version="0.50.0",
            migration_head="0025_sprint50",
            evidence_json={"generation": 0},
            blockers_json=[],
            checksum_sha256="c" * 64,
            retention_class="final",
            retain_until=None,
            generated_by_admin_id=admin1,
            generated_at=now - timedelta(days=50),
        )
        db.add_all([old, newest, final])
        db.commit()
        old_id, newest_id, final_id = old.id, newest.id, final.id
        deleted = LaunchCommandService(db, get_settings()).prune_expired_working_evidence()
        assert deleted == 1
        assert db.get(LaunchEvidencePackEntity, old_id) is None
        assert db.get(LaunchEvidencePackEntity, newest_id) is not None
        assert db.get(LaunchEvidencePackEntity, final_id) is not None


def test_post_launch_review_is_durable_idempotent_and_advisory(client):
    program_id, zone_id = _basic_program_zone(
        area=f"Sprint50 Review {uuid4()}", status="live", rollout_stage="canary"
    )
    with SessionLocal() as db:
        traffic = LaunchTrafficGovernanceService(db, get_settings())
        traffic.refresh_all_live_zones()  # no chefs -> durable RED evidence
        review_svc = PostLaunchStabilizationService(db, get_settings())
        first = review_svc.refresh_review(zone_id=zone_id, generated_by="worker")
        second = review_svc.refresh_review(zone_id=zone_id, generated_by="admin")
        assert first.id == second.id
        assert second.status == "blocked"
        assert second.recommendation == "pause"
        db.expire_all()
        # Review is advice only: it must not itself mutate rollout state.
        assert db.get(ExpansionZoneEntity, zone_id).status == "live"
        assert len(
            list(
                db.scalars(
                    select(ExpansionReviewEntity).where(
                        ExpansionReviewEntity.zone_id == zone_id
                    )
                ).all()
            )
        ) == 1


def test_sprint50_reuses_existing_worker_job_count(client):
    with SessionLocal() as db:
        jobs = BackgroundJobService(db, get_settings()).schedule_maintenance()
        assert len(jobs) == 13
        assert any(x.job_type == "expansion.monitor" for x in jobs)
        assert any(x.job_type == "launch.command.maintain" for x in jobs)


def test_production_requires_sprint50_fail_closed_automation_controls():
    base = dict(
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
    )
    try:
        Settings(**base)
        assert False, "production should reject disabled Sprint 50 controls"
    except ValueError as exc:
        text = str(exc)
        assert "BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED must be true" in text
        assert "BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED must be true" in text

    strong = Settings(
        **base,
        slo_auto_pause_default_enabled=True,
        launch_daily_close_cadence_enabled=True,
    )
    assert strong.release_version == "0.50.0"
