from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    ChefProfileEntity,
    ChefWorkdayEntity,
    DriverProfileEntity,
    ExpansionCapacityForecastEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionZoneEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    ZoneAdmissionEventEntity,
    ZoneTrafficPolicyEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.launch_governance.schemas import (
    AdmissionDecision,
    AdmissionEventResponse,
    CapacityForecastResponse,
    MonitoringSnapshotResponse,
    TrafficPolicyResponse,
    TrafficCapsResponse,
    TrafficCapsUpdate,
    TrafficPolicyUpdate,
    TrafficZoneOverview,
)


ACTIVE_ORDER_STATUSES = (
    "pending_payment",
    "confirmed",
    "accepted_by_chef",
    "preparing",
    "ready_for_pickup",
    "assigned_to_driver",
    "picked_up",
    "out_for_delivery",
    "delivered",
)


@dataclass(slots=True)
class AdmissionReservation:
    decision: AdmissionDecision
    event: ZoneAdmissionEventEntity | None


class LaunchTrafficGovernanceService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    # ------------------------------------------------------------------
    # Zone / policy
    # ------------------------------------------------------------------
    def _zone(self, zone_id: UUID) -> ExpansionZoneEntity:
        row = self.db.get(ExpansionZoneEntity, zone_id)
        if row is None:
            raise ApiError(
                404,
                "expansion_zone_not_found",
                "منطقة التوسع غير موجودة.",
            )
        return row

    def zone_for_area(self, area: str | None) -> ExpansionZoneEntity | None:
        normalized = (area or "").strip()
        if not normalized:
            return None
        return self.db.scalar(
            select(ExpansionZoneEntity)
            .where(func.lower(ExpansionZoneEntity.area) == normalized.lower())
            .limit(1)
        )

    def _new_policy(
        self,
        *,
        zone: ExpansionZoneEntity,
        admin_id: UUID | None = None,
    ) -> ZoneTrafficPolicyEntity:
        row = ZoneTrafficPolicyEntity(
            zone_id=zone.id,
            is_enabled=True,
            hourly_order_cap=self.settings.traffic_default_hourly_order_cap,
            chef_daily_order_cap=self.settings.traffic_default_chef_daily_order_cap,
            enforce_rollout_bucket=True,
            warning_utilization_pct=self.settings.traffic_warning_utilization_pct,
            critical_utilization_pct=self.settings.traffic_critical_utilization_pct,
            rejection_spike_pct=self.settings.traffic_rejection_spike_pct,
            rejection_spike_min_attempts=self.settings.traffic_rejection_spike_min_attempts,
            slo_auto_pause_enabled=self.settings.slo_auto_pause_default_enabled,
            slo_consecutive_red_snapshots=self.settings.slo_consecutive_red_snapshots,
            note="Sprint 50 traffic/SLO policy",
            created_by_admin_id=admin_id,
            updated_by_admin_id=admin_id,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def policy(
        self,
        zone_id: UUID,
        *,
        lock: bool = False,
    ) -> ZoneTrafficPolicyEntity:
        zone = self._zone(zone_id)
        stmt = select(ZoneTrafficPolicyEntity).where(
            ZoneTrafficPolicyEntity.zone_id == zone_id
        )
        if lock:
            stmt = stmt.with_for_update()
        row = self.db.scalar(stmt)
        if row is None:
            row = self._new_policy(zone=zone)
        return row

    def policy_response(self, zone_id: UUID) -> TrafficPolicyResponse:
        row = self.policy(zone_id)
        return TrafficPolicyResponse.model_validate(row)

    def update_policy(
        self,
        *,
        zone_id: UUID,
        payload: TrafficPolicyUpdate,
        admin_id: UUID,
        request_id: str | None,
    ) -> TrafficPolicyResponse:
        row = self.policy(zone_id, lock=True)
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        row.updated_by_admin_id = admin_id

        self.audit.add(
            action="traffic.policy.updated",
            actor_user_id=admin_id,
            entity_type="zone_traffic_policy",
            entity_id=str(zone_id),
            request_id=request_id,
            metadata=payload.model_dump(mode="json"),
        )
        self.db.commit()
        self.db.refresh(row)
        return TrafficPolicyResponse.model_validate(row)

    def update_caps(
        self,
        *,
        zone_id: UUID,
        payload: TrafficCapsUpdate,
        admin_id: UUID,
        request_id: str | None,
    ) -> TrafficCapsResponse:
        zone = self._zone(zone_id)
        policy = self.policy(zone_id, lock=True)
        fields = payload.model_fields_set
        if "daily_order_cap" in fields:
            zone.daily_order_cap = payload.daily_order_cap
        if "hourly_order_cap" in fields:
            policy.hourly_order_cap = payload.hourly_order_cap
        if "chef_daily_order_cap" in fields:
            policy.chef_daily_order_cap = payload.chef_daily_order_cap
        policy.updated_by_admin_id = admin_id
        self.audit.add(
            action="traffic.caps.updated",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={
                "daily_order_cap": zone.daily_order_cap,
                "hourly_order_cap": policy.hourly_order_cap,
                "chef_daily_order_cap": policy.chef_daily_order_cap,
            },
        )
        self.db.commit()
        return TrafficCapsResponse(
            zone_id=zone.id,
            daily_order_cap=zone.daily_order_cap,
            hourly_order_cap=policy.hourly_order_cap,
            chef_daily_order_cap=policy.chef_daily_order_cap,
        )

    # ------------------------------------------------------------------
    # Admission
    # ------------------------------------------------------------------
    @staticmethod
    def rollout_bucket(zone_id: UUID, customer_id: UUID) -> int:
        digest = hashlib.sha256(
            f"{zone_id}:{customer_id}".encode("utf-8")
        ).hexdigest()
        return int(digest[:12], 16) % 100

    def _area_order_count(
        self,
        *,
        zone: ExpansionZoneEntity,
        service_date: date | None = None,
        created_since=None,
    ) -> int:
        stmt = (
            select(func.count(OrderEntity.id))
            .join(
                OrderDeliveryAddressEntity,
                OrderDeliveryAddressEntity.order_id == OrderEntity.id,
            )
            .where(
                func.lower(OrderDeliveryAddressEntity.area)
                == zone.area.lower(),
                OrderEntity.status.in_(ACTIVE_ORDER_STATUSES),
            )
        )
        if service_date is not None:
            stmt = stmt.where(OrderEntity.service_date == service_date)
        if created_since is not None:
            stmt = stmt.where(OrderEntity.created_at >= created_since)
        return int(self.db.scalar(stmt) or 0)

    def _chef_order_count(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        exclude_order_id: UUID | None = None,
    ) -> int:
        stmt = select(func.count(OrderEntity.id)).where(
            OrderEntity.chef_id == chef_id,
            OrderEntity.service_date == service_date,
            OrderEntity.status.in_(ACTIVE_ORDER_STATUSES),
        )
        if exclude_order_id is not None:
            stmt = stmt.where(OrderEntity.id != exclude_order_id)
        return int(self.db.scalar(stmt) or 0)

    def _record_event(
        self,
        *,
        zone: ExpansionZoneEntity,
        customer_id: UUID,
        chef_id: UUID,
        service_date: date,
        area: str,
        decision: str,
        reason: str,
        rollout_bucket: int | None,
        daily_cap: int | None,
        daily_usage_before: int,
        hourly_cap: int | None,
        hourly_usage_before: int,
        chef_daily_cap: int | None,
        chef_usage_before: int,
        request_id: str | None,
    ) -> ZoneAdmissionEventEntity:
        event = ZoneAdmissionEventEntity(
            zone_id=zone.id,
            customer_id=customer_id,
            chef_id=chef_id,
            service_date=service_date,
            area=area,
            decision=decision,
            reason=reason,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            rollout_bucket=rollout_bucket,
            daily_cap=daily_cap,
            daily_usage_before=daily_usage_before,
            hourly_cap=hourly_cap,
            hourly_usage_before=hourly_usage_before,
            chef_daily_cap=chef_daily_cap,
            chef_usage_before=chef_usage_before,
            request_id=request_id,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def admit_or_raise(
        self,
        *,
        customer_id: UUID,
        chef_id: UUID,
        service_date: date,
        area: str | None,
        request_id: str | None,
        exclude_order_id: UUID | None = None,
    ) -> AdmissionReservation:
        zone = self.zone_for_area(area)
        if zone is None:
            return AdmissionReservation(
                decision=AdmissionDecision(
                    governed=False,
                    admitted=True,
                    reason="area_not_governed",
                ),
                event=None,
            )

        # Lock the one policy row for this Zone so simultaneous checkout
        # admissions serialize before they inspect live cap usage.
        policy = self.policy(zone.id, lock=True)
        bucket = self.rollout_bucket(zone.id, customer_id)
        daily_cap = zone.daily_order_cap
        daily_usage = self._area_order_count(
            zone=zone,
            service_date=service_date,
        )
        hourly_cap = policy.hourly_order_cap
        hourly_usage = self._area_order_count(
            zone=zone,
            created_since=utc_now() - timedelta(hours=1),
        )
        chef_cap = policy.chef_daily_order_cap
        chef_usage = self._chef_order_count(
            chef_id=chef_id,
            service_date=service_date,
            exclude_order_id=exclude_order_id,
        )

        reason = "admitted"
        if not policy.is_enabled:
            reason = "traffic_policy_disabled"
        elif zone.status == "paused" or zone.rollout_stage == "paused":
            reason = "zone_paused"
        elif zone.status != "live" or zone.rollout_stage not in {
            "canary",
            "limited",
            "full",
        }:
            reason = "rollout_not_live"
        elif (
            policy.enforce_rollout_bucket
            and zone.rollout_percent < 100
            and bucket >= zone.rollout_percent
        ):
            reason = "outside_rollout_bucket"
        elif daily_cap is not None and daily_usage >= daily_cap:
            reason = "zone_daily_cap_reached"
        elif hourly_cap is not None and hourly_usage >= hourly_cap:
            reason = "zone_hourly_cap_reached"
        elif chef_cap is not None and chef_usage >= chef_cap:
            reason = "chef_daily_cap_reached"

        admitted = reason == "admitted"
        event = self._record_event(
            zone=zone,
            customer_id=customer_id,
            chef_id=chef_id,
            service_date=service_date,
            area=(area or zone.area).strip(),
            decision="admitted" if admitted else "rejected",
            reason=reason,
            rollout_bucket=bucket,
            daily_cap=daily_cap,
            daily_usage_before=daily_usage,
            hourly_cap=hourly_cap,
            hourly_usage_before=hourly_usage,
            chef_daily_cap=chef_cap,
            chef_usage_before=chef_usage,
            request_id=request_id,
        )
        decision = AdmissionDecision(
            governed=True,
            admitted=admitted,
            zone_id=zone.id,
            reason=reason,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            rollout_bucket=bucket,
            daily_cap=daily_cap,
            daily_usage_before=daily_usage,
            hourly_cap=hourly_cap,
            hourly_usage_before=hourly_usage,
            chef_daily_cap=chef_cap,
            chef_usage_before=chef_usage,
            event_id=event.id,
        )

        if admitted:
            return AdmissionReservation(decision=decision, event=event)

        self.audit.add(
            action="traffic.admission.rejected",
            actor_user_id=customer_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata=decision.model_dump(mode="json"),
        )
        # Rejected admission is useful operational evidence and must survive the
        # HTTP 409. Commit only the rejection decision, then fail closed.
        self.db.commit()
        raise ApiError(
            409,
            "expansion_capacity_unavailable",
            "المنطقة غير متاحة لطلب جديد الآن. حاول مرة أخرى لاحقًا.",
            {
                "zone_id": str(zone.id),
                "reason": reason,
                "rollout_stage": zone.rollout_stage,
                "rollout_percent": zone.rollout_percent,
            },
        )

    def attach_admitted_order(
        self,
        *,
        reservation: AdmissionReservation | None,
        order_id: UUID,
        request_id: str | None,
    ) -> None:
        if reservation is None or reservation.event is None:
            return
        reservation.event.order_id = order_id
        self.audit.add(
            action="traffic.admission.admitted",
            actor_user_id=reservation.event.customer_id,
            entity_type="order",
            entity_id=str(order_id),
            request_id=request_id,
            metadata=reservation.decision.model_dump(mode="json"),
        )

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------
    @staticmethod
    def _utilization(used: int, cap: int | None) -> float:
        if cap is None or cap <= 0:
            return 0.0
        return round((used / cap) * 100.0, 2)

    def refresh_monitoring(
        self,
        *,
        zone_id: UUID,
        service_date: date | None = None,
        generated_by: str = "admin",
    ) -> MonitoringSnapshotResponse:
        zone = self._zone(zone_id)
        policy = self.policy(zone.id)
        day = service_date or utc_now().date()
        one_hour_ago = utc_now() - timedelta(hours=1)

        daily_orders = self._area_order_count(
            zone=zone,
            service_date=day,
        )
        hourly_orders = self._area_order_count(
            zone=zone,
            created_since=one_hour_ago,
        )
        attempts = int(
            self.db.scalar(
                select(func.count(ZoneAdmissionEventEntity.id)).where(
                    ZoneAdmissionEventEntity.zone_id == zone.id,
                    ZoneAdmissionEventEntity.created_at >= one_hour_ago,
                )
            )
            or 0
        )
        rejections = int(
            self.db.scalar(
                select(func.count(ZoneAdmissionEventEntity.id)).where(
                    ZoneAdmissionEventEntity.zone_id == zone.id,
                    ZoneAdmissionEventEntity.created_at >= one_hour_ago,
                    ZoneAdmissionEventEntity.decision == "rejected",
                )
            )
            or 0
        )
        rejection_rate = round(
            (rejections / attempts) * 100.0,
            2,
        ) if attempts else 0.0

        available_drivers = int(
            self.db.scalar(
                select(func.count(DriverProfileEntity.user_id)).where(
                    DriverProfileEntity.status == "available"
                )
            )
            or 0
        )
        open_chefs = int(
            self.db.scalar(
                select(func.count(ChefWorkdayEntity.id))
                .join(
                    ChefProfileEntity,
                    ChefProfileEntity.user_id == ChefWorkdayEntity.chef_id,
                )
                .where(
                    ChefWorkdayEntity.service_date == day,
                    ChefWorkdayEntity.status == "open",
                    func.lower(ChefProfileEntity.area) == zone.area.lower(),
                )
            )
            or 0
        )
        top_chef_orders = int(
            self.db.scalar(
                select(func.count(OrderEntity.id))
                .where(
                    OrderEntity.service_date == day,
                    OrderEntity.status.in_(ACTIVE_ORDER_STATUSES),
                )
                .group_by(OrderEntity.chef_id)
                .order_by(func.count(OrderEntity.id).desc())
                .limit(1)
            )
            or 0
        )

        daily_util = self._utilization(daily_orders, zone.daily_order_cap)
        hourly_util = self._utilization(hourly_orders, policy.hourly_order_cap)
        chef_util = self._utilization(
            top_chef_orders,
            policy.chef_daily_order_cap,
        )

        blockers: list[str] = []
        severity = 0  # 0 green, 1 amber, 2 red

        if zone.status == "paused" or zone.rollout_stage == "paused":
            blockers.append("zone_paused")
            severity = max(severity, 2)

        for label, value in [
            ("daily_capacity", daily_util),
            ("hourly_capacity", hourly_util),
            ("chef_capacity", chef_util),
        ]:
            if value >= policy.critical_utilization_pct:
                blockers.append(f"{label}_critical")
                severity = max(severity, 2)
            elif value >= policy.warning_utilization_pct:
                blockers.append(f"{label}_warning")
                severity = max(severity, 1)

        if (
            attempts >= policy.rejection_spike_min_attempts
            and rejection_rate >= policy.rejection_spike_pct
        ):
            blockers.append("admission_rejection_spike")
            severity = max(
                severity,
                2
                if rejection_rate >= min(100.0, policy.rejection_spike_pct * 2)
                else 1,
            )

        if daily_orders > 0 and available_drivers == 0:
            blockers.append("no_available_driver_pool")
            severity = max(severity, 1)

        if zone.status == "live" and day == utc_now().date() and open_chefs == 0:
            blockers.append("no_open_chefs")
            severity = max(severity, 2)

        health = ("green", "amber", "red")[severity]
        row = ExpansionMonitoringSnapshotEntity(
            zone_id=zone.id,
            service_date=day,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            zone_daily_cap=zone.daily_order_cap,
            admitted_orders_today=daily_orders,
            daily_utilization_pct=daily_util,
            hourly_cap=policy.hourly_order_cap,
            admitted_orders_last_hour=hourly_orders,
            hourly_utilization_pct=hourly_util,
            admission_attempts_last_hour=attempts,
            admission_rejections_last_hour=rejections,
            rejection_rate_pct=rejection_rate,
            available_drivers=available_drivers,
            open_chefs=open_chefs,
            top_chef_orders=top_chef_orders,
            chef_daily_cap=policy.chef_daily_order_cap,
            top_chef_utilization_pct=chef_util,
            health=health,
            blockers_json=blockers,
            generated_by=generated_by,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return MonitoringSnapshotResponse.model_validate(row)

    def capacity_forecast_for_snapshot(
        self,
        snapshot_id: UUID,
    ) -> CapacityForecastResponse:
        existing = self.db.scalar(
            select(ExpansionCapacityForecastEntity).where(
                ExpansionCapacityForecastEntity.monitoring_snapshot_id == snapshot_id
            )
        )
        if existing is not None:
            return CapacityForecastResponse.model_validate(existing)

        snapshot = self.db.get(ExpansionMonitoringSnapshotEntity, snapshot_id)
        if snapshot is None:
            raise ApiError(404, "monitoring_snapshot_not_found", "Monitoring snapshot غير موجودة.")
        policy = self.policy(snapshot.zone_id)
        sample_rows = list(
            self.db.scalars(
                select(ExpansionMonitoringSnapshotEntity)
                .where(
                    ExpansionMonitoringSnapshotEntity.zone_id == snapshot.zone_id,
                    ExpansionMonitoringSnapshotEntity.rollout_stage.in_(["canary", "limited", "full"]),
                )
                .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
                .limit(self.settings.slo_capacity_forecast_lookback_snapshots)
            ).all()
        )
        if not sample_rows:
            sample_rows = [snapshot]

        rolling_hourly = sum(x.admitted_orders_last_hour for x in sample_rows) / len(sample_rows)
        # Conservative near-term forecast: never forecast below the most recent observed rate.
        projected = round(max(float(snapshot.admitted_orders_last_hour), rolling_hourly), 2)
        projected_util = (
            round(projected / snapshot.hourly_cap * 100.0, 2)
            if snapshot.hourly_cap and snapshot.hourly_cap > 0
            else 0.0
        )
        headroom = (
            max(0, snapshot.zone_daily_cap - snapshot.admitted_orders_today)
            if snapshot.zone_daily_cap is not None
            else None
        )
        minutes_to_daily_cap = (
            math.ceil((headroom / projected) * 60)
            if headroom is not None and projected > 0
            else None
        )

        reasons: list[str] = []
        risk_level = 0
        if snapshot.health == "red":
            reasons.append("current_monitoring_red")
            risk_level = 2
        elif snapshot.health == "amber":
            reasons.append("current_monitoring_amber")
            risk_level = 1

        if projected_util >= policy.critical_utilization_pct:
            reasons.append("projected_hourly_capacity_critical")
            risk_level = max(risk_level, 2)
        elif projected_util >= policy.warning_utilization_pct:
            reasons.append("projected_hourly_capacity_warning")
            risk_level = max(risk_level, 1)

        if headroom == 0 and snapshot.zone_daily_cap is not None:
            reasons.append("daily_capacity_exhausted")
            risk_level = 2
        elif minutes_to_daily_cap is not None and minutes_to_daily_cap <= 120:
            reasons.append("daily_capacity_within_two_hours")
            risk_level = max(risk_level, 1)

        row = ExpansionCapacityForecastEntity(
            zone_id=snapshot.zone_id,
            monitoring_snapshot_id=snapshot.id,
            service_date=snapshot.service_date,
            horizon_minutes=60,
            sample_count=len(sample_rows),
            current_orders_last_hour=snapshot.admitted_orders_last_hour,
            projected_orders_next_hour=projected,
            hourly_cap=snapshot.hourly_cap,
            projected_hourly_utilization_pct=projected_util,
            current_daily_orders=snapshot.admitted_orders_today,
            daily_cap=snapshot.zone_daily_cap,
            daily_headroom_orders=headroom,
            projected_minutes_to_daily_cap=minutes_to_daily_cap,
            risk=("green", "amber", "red")[risk_level],
            reasons_json=reasons,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return CapacityForecastResponse.model_validate(row)

    def capacity_forecasts(
        self,
        *,
        zone_id: UUID,
        limit: int = 100,
    ) -> list[CapacityForecastResponse]:
        self._zone(zone_id)
        rows = list(
            self.db.scalars(
                select(ExpansionCapacityForecastEntity)
                .where(ExpansionCapacityForecastEntity.zone_id == zone_id)
                .order_by(ExpansionCapacityForecastEntity.generated_at.desc())
                .limit(limit)
            ).all()
        )
        return [CapacityForecastResponse.model_validate(x) for x in rows]

    def latest_capacity_forecast(
        self,
        zone_id: UUID,
    ) -> CapacityForecastResponse | None:
        row = self.db.scalar(
            select(ExpansionCapacityForecastEntity)
            .where(ExpansionCapacityForecastEntity.zone_id == zone_id)
            .order_by(ExpansionCapacityForecastEntity.generated_at.desc())
            .limit(1)
        )
        return CapacityForecastResponse.model_validate(row) if row is not None else None

    def _consecutive_red_streak(self, zone_id: UUID, required: int) -> int:
        rows = list(
            self.db.scalars(
                select(ExpansionMonitoringSnapshotEntity)
                .where(ExpansionMonitoringSnapshotEntity.zone_id == zone_id)
                .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
                .limit(max(required + 5, 10))
            ).all()
        )
        streak = 0
        for row in rows:
            if row.rollout_stage not in {"canary", "limited", "full"}:
                break
            if row.health != "red":
                break
            streak += 1
        return streak

    def _evaluate_slo_auto_pause(
        self,
        *,
        zone: ExpansionZoneEntity,
        snapshot: MonitoringSnapshotResponse,
    ) -> bool:
        if zone.status != "live" or zone.rollout_stage not in {"canary", "limited", "full"}:
            return False
        policy = self.policy(zone.id)
        if not policy.slo_auto_pause_enabled or snapshot.health != "red":
            return False
        required = policy.slo_consecutive_red_snapshots
        streak = self._consecutive_red_streak(zone.id, required)
        if streak < required:
            return False

        # Local import keeps Launch Governance independent at module import time.
        from app.modules.financial_automation.service import FinancialAutomationService

        result = FinancialAutomationService(self.db, self.settings).auto_pause_rollout(
            zone_id=zone.id,
            monitoring_snapshot_id=snapshot.id,
            blockers=snapshot.blockers_json,
            red_streak=streak,
            required_red_streak=required,
        )
        return result is not None

    def refresh_all_live_zones(self) -> dict:
        zones = list(
            self.db.scalars(
                select(ExpansionZoneEntity).where(
                    ExpansionZoneEntity.status.in_(["live", "paused"])
                )
            ).all()
        )
        by_health = {"green": 0, "amber": 0, "red": 0}
        forecast_risk = {"green": 0, "amber": 0, "red": 0}
        auto_paused = 0
        for zone in zones:
            was_live = zone.status == "live" and zone.rollout_stage in {"canary", "limited", "full"}
            snapshot = self.refresh_monitoring(
                zone_id=zone.id,
                generated_by="worker",
            )
            by_health[snapshot.health] += 1
            forecast = self.capacity_forecast_for_snapshot(snapshot.id)
            forecast_risk[forecast.risk] += 1
            if was_live and self._evaluate_slo_auto_pause(zone=zone, snapshot=snapshot):
                auto_paused += 1
        return {
            "zones_scanned": len(zones),
            "health": by_health,
            "capacity_forecast_risk": forecast_risk,
            "auto_paused": auto_paused,
        }

    def latest_monitoring(
        self,
        zone_id: UUID,
    ) -> MonitoringSnapshotResponse | None:
        self._zone(zone_id)
        row = self.db.scalar(
            select(ExpansionMonitoringSnapshotEntity)
            .where(ExpansionMonitoringSnapshotEntity.zone_id == zone_id)
            .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
            .limit(1)
        )
        return (
            MonitoringSnapshotResponse.model_validate(row)
            if row is not None
            else None
        )

    def monitoring_history(
        self,
        *,
        zone_id: UUID,
        limit: int = 100,
    ) -> list[MonitoringSnapshotResponse]:
        self._zone(zone_id)
        rows = list(
            self.db.scalars(
                select(ExpansionMonitoringSnapshotEntity)
                .where(ExpansionMonitoringSnapshotEntity.zone_id == zone_id)
                .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
                .limit(limit)
            ).all()
        )
        return [
            MonitoringSnapshotResponse.model_validate(x)
            for x in rows
        ]

    def admissions(
        self,
        *,
        zone_id: UUID,
        decision: str | None,
        reason: str | None,
        limit: int,
    ) -> list[AdmissionEventResponse]:
        self._zone(zone_id)
        stmt = select(ZoneAdmissionEventEntity).where(
            ZoneAdmissionEventEntity.zone_id == zone_id
        )
        if decision:
            stmt = stmt.where(
                ZoneAdmissionEventEntity.decision == decision
            )
        if reason:
            stmt = stmt.where(
                ZoneAdmissionEventEntity.reason == reason
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(
                    ZoneAdmissionEventEntity.created_at.desc()
                ).limit(limit)
            ).all()
        )
        return [
            AdmissionEventResponse.model_validate(x)
            for x in rows
        ]

    def zone_overviews(self) -> list[TrafficZoneOverview]:
        zones = list(
            self.db.scalars(
                select(ExpansionZoneEntity).order_by(
                    ExpansionZoneEntity.created_at.desc()
                )
            ).all()
        )
        result: list[TrafficZoneOverview] = []
        for zone in zones:
            result.append(
                TrafficZoneOverview(
                    zone_id=zone.id,
                    area=zone.area,
                    zone_status=zone.status,
                    rollout_stage=zone.rollout_stage,
                    rollout_percent=zone.rollout_percent,
                    daily_order_cap=zone.daily_order_cap,
                    policy=TrafficPolicyResponse.model_validate(
                        self.policy(zone.id)
                    ),
                    latest_monitoring=self.latest_monitoring(zone.id),
                    latest_forecast=self.latest_capacity_forecast(zone.id),
                )
            )
        return result
