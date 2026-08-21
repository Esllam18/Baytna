from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    DailyFinancialCloseEntity,
    ExpansionCapacityForecastEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionReviewEntity,
    ExpansionRolloutEventEntity,
    ExpansionZoneEntity,
    LaunchCommandSessionEntity,
    OperationsIncidentEntity,
)
from app.core.errors import ApiError
from app.core.security import utc_now
from app.modules.post_launch.schemas import ExpansionReviewResponse, PostLaunchSummary


class PostLaunchStabilizationService:
    """Sprint 50 post-launch review layer.

    This service is deliberately advisory. It summarizes durable traffic,
    finance and incident evidence but never resumes traffic, increases caps or
    advances a rollout stage.
    """

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def _zone(self, zone_id: UUID) -> ExpansionZoneEntity:
        row = self.db.get(ExpansionZoneEntity, zone_id)
        if row is None:
            raise ApiError(404, "expansion_zone_not_found", "منطقة التوسع غير موجودة.")
        return row

    def _latest_session(self, zone_id: UUID) -> LaunchCommandSessionEntity | None:
        return self.db.scalar(
            select(LaunchCommandSessionEntity)
            .where(
                LaunchCommandSessionEntity.zone_id == zone_id,
                LaunchCommandSessionEntity.status != "aborted",
            )
            .order_by(LaunchCommandSessionEntity.created_at.desc())
            .limit(1)
        )

    def _review_window(self, review_date: date) -> tuple[date, date]:
        days = max(1, self.settings.launch_expansion_review_window_days)
        return review_date - timedelta(days=days - 1), review_date

    def refresh_review(
        self,
        *,
        zone_id: UUID,
        generated_by: str,
        review_date: date | None = None,
        create_only: bool = False,
    ) -> ExpansionReviewResponse:
        zone = self._zone(zone_id)
        today = review_date or utc_now().date()
        window_start, window_end = self._review_window(today)
        existing = self.db.scalar(
            select(ExpansionReviewEntity).where(
                ExpansionReviewEntity.zone_id == zone_id,
                ExpansionReviewEntity.review_date == today,
            )
        )
        if existing is not None and create_only:
            return ExpansionReviewResponse.model_validate(existing)

        snapshots = list(
            self.db.scalars(
                select(ExpansionMonitoringSnapshotEntity).where(
                    ExpansionMonitoringSnapshotEntity.zone_id == zone_id,
                    ExpansionMonitoringSnapshotEntity.service_date >= window_start,
                    ExpansionMonitoringSnapshotEntity.service_date <= window_end,
                )
            ).all()
        )
        red = sum(x.health == "red" for x in snapshots)
        amber = sum(x.health == "amber" for x in snapshots)
        latest_monitoring = max(snapshots, key=lambda x: x.observed_at, default=None)

        start_at = datetime.combine(window_start, time.min, tzinfo=timezone.utc)
        end_at = datetime.combine(window_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
        auto_pause_events = int(
            self.db.scalar(
                select(func.count(ExpansionRolloutEventEntity.id)).where(
                    ExpansionRolloutEventEntity.zone_id == zone_id,
                    ExpansionRolloutEventEntity.trigger_source == "system",
                    ExpansionRolloutEventEntity.trigger_reason == "slo_auto_pause",
                    ExpansionRolloutEventEntity.created_at >= start_at,
                    ExpansionRolloutEventEntity.created_at < end_at,
                )
            )
            or 0
        )

        latest_forecast = self.db.scalar(
            select(ExpansionCapacityForecastEntity)
            .where(ExpansionCapacityForecastEntity.zone_id == zone_id)
            .order_by(ExpansionCapacityForecastEntity.generated_at.desc())
            .limit(1)
        )
        session = self._latest_session(zone_id)
        required_closes = closed_closes = overdue_closes = blocked_closes = 0
        close_ids: list[str] = []
        if session is not None:
            stabilization_last = session.launch_date + timedelta(
                days=max(1, self.settings.launch_post_launch_stabilization_days) - 1
            )
            due_end = min(today - timedelta(days=1), stabilization_last)
            if due_end >= session.launch_date:
                required_closes = (due_end - session.launch_date).days + 1
            closes = list(
                self.db.scalars(
                    select(DailyFinancialCloseEntity).where(
                        DailyFinancialCloseEntity.session_id == session.id,
                        DailyFinancialCloseEntity.close_date >= window_start,
                        DailyFinancialCloseEntity.close_date <= window_end,
                    )
                ).all()
            )
            closed_closes = sum(x.status == "closed" for x in closes)
            overdue_closes = sum(x.overdue_notified_at is not None and x.status != "closed" for x in closes)
            blocked_closes = sum(x.status == "blocked" for x in closes)
            close_ids = [str(x.id) for x in closes]

        critical_incidents = int(
            self.db.scalar(
                select(func.count(OperationsIncidentEntity.id)).where(
                    OperationsIncidentEntity.source_id == str(zone_id),
                    OperationsIncidentEntity.status.in_(["open", "acknowledged"]),
                    OperationsIncidentEntity.severity == "critical",
                )
            )
            or 0
        )

        blockers: list[str] = []
        if latest_monitoring is None:
            blockers.append("monitoring_missing")
        elif latest_monitoring.health == "red":
            blockers.append("latest_monitoring_red")
        if critical_incidents:
            blockers.append("critical_incident_open")
        if overdue_closes:
            blockers.append("daily_close_overdue")
        if blocked_closes:
            blockers.append("daily_close_blocked")
        if required_closes > closed_closes + blocked_closes + overdue_closes:
            blockers.append("daily_close_cadence_incomplete")

        watch_reasons: list[str] = []
        if latest_monitoring is not None and latest_monitoring.health == "amber":
            watch_reasons.append("latest_monitoring_amber")
        if auto_pause_events:
            watch_reasons.append("recent_slo_auto_pause")
        if latest_forecast is not None and latest_forecast.risk in {"amber", "red"}:
            watch_reasons.append(f"capacity_forecast_{latest_forecast.risk}")
        if amber:
            watch_reasons.append("amber_snapshots_present")

        if blockers:
            status = "blocked"
            recommendation = "pause" if zone.status == "live" else "hold"
        elif watch_reasons:
            status = "watch"
            recommendation = "hold"
        else:
            status = "healthy"
            recommendation = "continue"

        evidence = {
            "zone_status": zone.status,
            "rollout_stage": zone.rollout_stage,
            "rollout_percent": zone.rollout_percent,
            "latest_monitoring_snapshot_id": str(latest_monitoring.id) if latest_monitoring else None,
            "latest_monitoring_health": latest_monitoring.health if latest_monitoring else None,
            "latest_forecast_id": str(latest_forecast.id) if latest_forecast else None,
            "latest_forecast_risk": latest_forecast.risk if latest_forecast else None,
            "critical_incidents": critical_incidents,
            "watch_reasons": sorted(set(watch_reasons)),
            "close_ids": close_ids,
            "review_window_days": self.settings.launch_expansion_review_window_days,
        }

        if existing is None:
            row = ExpansionReviewEntity(
                zone_id=zone_id,
                session_id=session.id if session else None,
                review_date=today,
                window_start=window_start,
                window_end=window_end,
                status=status,
                recommendation=recommendation,
                generated_by=generated_by,
            )
            self.db.add(row)
        else:
            row = existing
            row.session_id = session.id if session else None
            row.window_start = window_start
            row.window_end = window_end
            row.status = status
            row.recommendation = recommendation
            row.generated_by = generated_by
            row.updated_at = utc_now()

        row.monitoring_snapshots = len(snapshots)
        row.red_snapshots = red
        row.amber_snapshots = amber
        row.auto_pause_events = auto_pause_events
        row.required_closes = required_closes
        row.closed_closes = closed_closes
        row.overdue_closes = overdue_closes
        row.blocked_closes = blocked_closes
        row.latest_forecast_risk = latest_forecast.risk if latest_forecast else None
        row.blockers_json = blockers
        row.evidence_json = evidence
        self.db.commit()
        self.db.refresh(row)
        return ExpansionReviewResponse.model_validate(row)

    def refresh_due_reviews(self) -> int:
        today = utc_now().date()
        zones = list(
            self.db.scalars(
                select(ExpansionZoneEntity).where(
                    ExpansionZoneEntity.rollout_stage.in_(["canary", "limited", "full", "paused"]),
                    ExpansionZoneEntity.status.in_(["live", "paused"]),
                )
            ).all()
        )
        created = 0
        for zone in zones:
            existing = self.db.scalar(
                select(ExpansionReviewEntity.id).where(
                    ExpansionReviewEntity.zone_id == zone.id,
                    ExpansionReviewEntity.review_date == today,
                )
            )
            if existing is not None:
                continue
            self.refresh_review(
                zone_id=zone.id,
                generated_by="worker",
                review_date=today,
                create_only=True,
            )
            created += 1
        return created

    def reviews(
        self,
        *,
        zone_id: UUID | None = None,
        limit: int = 200,
    ) -> list[ExpansionReviewResponse]:
        stmt = select(ExpansionReviewEntity)
        if zone_id is not None:
            stmt = stmt.where(ExpansionReviewEntity.zone_id == zone_id)
        rows = list(
            self.db.scalars(
                stmt.order_by(ExpansionReviewEntity.review_date.desc()).limit(limit)
            ).all()
        )
        return [ExpansionReviewResponse.model_validate(x) for x in rows]

    def summary(self) -> PostLaunchSummary:
        latest_by_zone = {}
        rows = list(
            self.db.scalars(
                select(ExpansionReviewEntity).order_by(
                    ExpansionReviewEntity.zone_id,
                    ExpansionReviewEntity.review_date.desc(),
                )
            ).all()
        )
        for row in rows:
            latest_by_zone.setdefault(row.zone_id, row)
        current = list(latest_by_zone.values())
        responses = [ExpansionReviewResponse.model_validate(x) for x in current]
        return PostLaunchSummary(
            zones_reviewed=len(current),
            healthy=sum(x.status == "healthy" for x in current),
            watch=sum(x.status == "watch" for x in current),
            blocked=sum(x.status == "blocked" for x in current),
            continue_count=sum(x.recommendation == "continue" for x in current),
            hold_count=sum(x.recommendation == "hold" for x in current),
            pause_count=sum(x.recommendation == "pause" for x in current),
            reviews=responses,
        )
