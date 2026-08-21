from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    DailyFinancialCloseEntity,
    EconomicsCostEntryEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionZoneEntity,
    LaunchCommandEventEntity,
    LaunchCommandSessionEntity,
    LaunchEvidencePackEntity,
    LaunchRollbackDrillEntity,
    LaunchRunbookStepEntity,
    LaunchTrafficOverrideEntity,
    OperationsIncidentEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    PaymentEntity,
    PaymentReconciliationIssueEntity,
    PilotProgramEntity,
    ProviderCostImportBatchEntity,
    ProviderSettlementBatchEntity,
    RefundEntity,
    UserEntity,
    ZoneTrafficPolicyEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.launch_command.schemas import (
    DailyFinancialCloseResponse,
    EvidencePackResponse,
    FinancialCloseActionRequest,
    FinancialClosePrepareRequest,
    LaunchCommandEventResponse,
    LaunchCommandOverview,
    LaunchRunbookStepResponse,
    LaunchSessionCreate,
    LaunchSessionResponse,
    RollbackDrillComplete,
    RollbackDrillCreate,
    RollbackDrillResponse,
    RunbookStepDecision,
    TrafficOverrideCreate,
    TrafficOverrideResponse,
)

MIGRATION_HEAD = "0025_sprint50"

RUNBOOK_TEMPLATE = [
    ("release_identity", 1, "release", "Release identity, migration and commit verified"),
    ("infrastructure_live", 2, "infra", "PostgreSQL, HTTPS API/Admin and deployment health verified"),
    ("mobile_builds", 3, "apps", "Customer, Chef and Driver pilot builds installed"),
    ("notifications_crash", 4, "observability", "FCM and Sentry evidence verified across apps"),
    ("payments_storage_sms", 5, "providers", "Paymob, S3 and Twilio live evidence verified"),
    ("economics_settlements", 6, "finance", "Economics complete and provider settlement operationally closed"),
    ("traffic_policy_caps", 7, "traffic", "Traffic policy, rollout bucket and caps verified"),
    ("rollback_drill", 8, "recovery", "Rollback drill passed within target"),
    ("canary_live_order", 9, "traffic", "Real Canary order admitted through governed checkout"),
    ("monitoring_green", 10, "operations", "Expansion monitoring is Green/acceptable"),
    ("daily_financial_close", 11, "finance", "Launch-day financial close completed"),
    ("operations_signoff", 12, "signoff", "Incident commander and operations owner signed off"),
]


def _bounds(day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time.min, tzinfo=timezone.utc),
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


class LaunchCommandService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    # ------------------------------------------------------------------
    # Common
    # ------------------------------------------------------------------
    def _admin(self, admin_id: UUID) -> UserEntity:
        row = self.db.get(UserEntity, admin_id)
        if row is None or row.role != "admin" or not row.is_active:
            raise ApiError(
                422,
                "launch_admin_invalid",
                "المستخدم المحدد ليس مسؤول إدارة نشطًا.",
            )
        return row

    def _session(self, session_id: UUID, *, lock: bool = False) -> LaunchCommandSessionEntity:
        stmt = select(LaunchCommandSessionEntity).where(
            LaunchCommandSessionEntity.id == session_id
        )
        if lock:
            stmt = stmt.with_for_update()
        row = self.db.scalar(stmt)
        if row is None:
            raise ApiError(404, "launch_session_not_found", "جلسة الإطلاق غير موجودة.")
        return row

    def _zone(self, zone_id: UUID) -> ExpansionZoneEntity:
        row = self.db.get(ExpansionZoneEntity, zone_id)
        if row is None:
            raise ApiError(404, "expansion_zone_not_found", "منطقة التوسع غير موجودة.")
        return row

    def _policy(self, zone_id: UUID, *, lock: bool = False) -> ZoneTrafficPolicyEntity:
        stmt = select(ZoneTrafficPolicyEntity).where(
            ZoneTrafficPolicyEntity.zone_id == zone_id
        )
        if lock:
            stmt = stmt.with_for_update()
        row = self.db.scalar(stmt)
        if row is None:
            raise ApiError(
                409,
                "zone_traffic_policy_missing",
                "Traffic Policy غير موجودة للمنطقة.",
            )
        return row

    def _event(
        self,
        *,
        session_id: UUID,
        event_type: str,
        title: str,
        severity: str = "info",
        actor_admin_id: UUID | None = None,
        details: dict | None = None,
    ) -> LaunchCommandEventEntity:
        row = LaunchCommandEventEntity(
            session_id=session_id,
            event_type=event_type,
            severity=severity,
            title=title,
            details_json=details or {},
            actor_admin_id=actor_admin_id,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _require_active_session(self, session_id: UUID) -> LaunchCommandSessionEntity:
        row = self._session(session_id, lock=True)
        if row.status != "active":
            raise ApiError(
                409,
                "launch_session_not_active",
                "يجب أن تكون جلسة الإطلاق Active.",
            )
        return row

    # ------------------------------------------------------------------
    # Sessions / runbook
    # ------------------------------------------------------------------
    def create_session(
        self,
        *,
        payload: LaunchSessionCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> LaunchSessionResponse:
        zone = self._zone(payload.zone_id)
        program = self.db.get(PilotProgramEntity, payload.pilot_program_id)
        if program is None:
            raise ApiError(404, "pilot_program_not_found", "برنامج الطيار غير موجود.")
        if zone.source_program_id != program.id:
            raise ApiError(
                409,
                "launch_program_zone_mismatch",
                "برنامج الطيار لا يطابق مصدر منطقة التوسع.",
            )
        for candidate in [
            payload.incident_commander_admin_id,
            payload.finance_admin_id,
            payload.operations_admin_id,
        ]:
            if candidate is not None:
                self._admin(candidate)

        existing = self.db.scalar(
            select(LaunchCommandSessionEntity).where(
                LaunchCommandSessionEntity.zone_id == zone.id,
                LaunchCommandSessionEntity.status.in_(["planned", "active", "paused"]),
            )
        )
        if existing is not None:
            raise ApiError(
                409,
                "launch_session_already_open",
                "يوجد Launch Command Session مفتوحة بالفعل لهذه المنطقة.",
                {"session_id": str(existing.id)},
            )

        row = LaunchCommandSessionEntity(
            pilot_program_id=program.id,
            zone_id=zone.id,
            launch_date=payload.launch_date,
            status="planned",
            incident_commander_admin_id=payload.incident_commander_admin_id,
            finance_admin_id=payload.finance_admin_id,
            operations_admin_id=payload.operations_admin_id,
            notes=payload.notes,
            created_by_admin_id=admin_id,
        )
        self.db.add(row)
        self.db.flush()

        for key, sequence, category, title in RUNBOOK_TEMPLATE:
            self.db.add(
                LaunchRunbookStepEntity(
                    session_id=row.id,
                    step_key=key,
                    sequence=sequence,
                    category=category,
                    title=title,
                    is_required=True,
                    status="pending",
                )
            )

        self._event(
            session_id=row.id,
            event_type="session.created",
            title="Launch Command Session created",
            actor_admin_id=admin_id,
            details={"zone_id": str(zone.id), "launch_date": payload.launch_date.isoformat()},
        )
        self.audit.add(
            action="launch.command.session.created",
            actor_user_id=admin_id,
            entity_type="launch_command_session",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"zone_id": str(zone.id), "program_id": str(program.id)},
        )
        self.db.commit()
        self.db.refresh(row)
        return LaunchSessionResponse.model_validate(row)

    def sessions(self, limit: int = 100) -> list[LaunchSessionResponse]:
        rows = list(
            self.db.scalars(
                select(LaunchCommandSessionEntity)
                .order_by(LaunchCommandSessionEntity.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [LaunchSessionResponse.model_validate(x) for x in rows]

    def start_session(
        self,
        *,
        session_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> LaunchSessionResponse:
        row = self._session(session_id, lock=True)
        if row.status != "planned":
            raise ApiError(409, "launch_session_not_planned", "يمكن بدء جلسة Planned فقط.")
        row.status = "active"
        row.started_at = utc_now()
        row.paused_at = None
        self._event(
            session_id=row.id,
            event_type="session.started",
            title="Launch command activated",
            actor_admin_id=admin_id,
        )
        self.audit.add(
            action="launch.command.session.started",
            actor_user_id=admin_id,
            entity_type="launch_command_session",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return LaunchSessionResponse.model_validate(row)

    def pause_session(self, *, session_id: UUID, admin_id: UUID, request_id: str | None) -> LaunchSessionResponse:
        row = self._session(session_id, lock=True)
        if row.status != "active":
            raise ApiError(409, "launch_session_not_active", "الجلسة ليست Active.")
        row.status = "paused"
        row.paused_at = utc_now()
        self._event(
            session_id=row.id,
            event_type="session.paused",
            title="Launch command paused",
            severity="warning",
            actor_admin_id=admin_id,
        )
        self.audit.add(
            action="launch.command.session.paused",
            actor_user_id=admin_id,
            entity_type="launch_command_session",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return LaunchSessionResponse.model_validate(row)

    def resume_session(self, *, session_id: UUID, admin_id: UUID, request_id: str | None) -> LaunchSessionResponse:
        row = self._session(session_id, lock=True)
        if row.status != "paused":
            raise ApiError(409, "launch_session_not_paused", "الجلسة ليست Paused.")
        row.status = "active"
        row.paused_at = None
        self._event(
            session_id=row.id,
            event_type="session.resumed",
            title="Launch command resumed",
            actor_admin_id=admin_id,
        )
        self.audit.add(
            action="launch.command.session.resumed",
            actor_user_id=admin_id,
            entity_type="launch_command_session",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return LaunchSessionResponse.model_validate(row)

    def abort_session(self, *, session_id: UUID, admin_id: UUID, request_id: str | None) -> LaunchSessionResponse:
        row = self._session(session_id, lock=True)
        if row.status not in {"planned", "active", "paused"}:
            raise ApiError(409, "launch_session_not_abortable", "الجلسة لا يمكن إلغاؤها.")
        self._revert_session_overrides(row.id, reverted_by_admin_id=admin_id, expired=False)
        self._recover_running_drills(row.id, actor_admin_id=admin_id, force_abort=True)
        row.status = "aborted"
        row.aborted_at = utc_now()
        self._event(
            session_id=row.id,
            event_type="session.aborted",
            title="Launch command aborted",
            severity="critical",
            actor_admin_id=admin_id,
        )
        self.audit.add(
            action="launch.command.session.aborted",
            actor_user_id=admin_id,
            entity_type="launch_command_session",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return LaunchSessionResponse.model_validate(row)

    def runbook(self, session_id: UUID) -> list[LaunchRunbookStepResponse]:
        self._session(session_id)
        rows = list(
            self.db.scalars(
                select(LaunchRunbookStepEntity)
                .where(LaunchRunbookStepEntity.session_id == session_id)
                .order_by(LaunchRunbookStepEntity.sequence.asc())
            ).all()
        )
        return [LaunchRunbookStepResponse.model_validate(x) for x in rows]

    def decide_runbook_step(
        self,
        *,
        session_id: UUID,
        step_key: str,
        payload: RunbookStepDecision,
        admin_id: UUID,
        request_id: str | None,
    ) -> LaunchRunbookStepResponse:
        session = self._session(session_id)
        if session.status not in {"active", "paused"}:
            raise ApiError(409, "launch_session_not_operational", "الجلسة ليست مفتوحة للتشغيل.")
        step = self.db.scalar(
            select(LaunchRunbookStepEntity).where(
                LaunchRunbookStepEntity.session_id == session_id,
                LaunchRunbookStepEntity.step_key == step_key,
            )
        )
        if step is None:
            raise ApiError(404, "launch_runbook_step_not_found", "Runbook step غير موجودة.")

        step.status = payload.status
        step.evidence_reference = (payload.evidence_reference or "").strip() or None
        step.note = payload.note
        if payload.status == "pending":
            step.completed_by_admin_id = None
            step.completed_at = None
        else:
            step.completed_by_admin_id = admin_id
            step.completed_at = utc_now()

        severity = "high" if payload.status == "failed" else "info"
        self._event(
            session_id=session_id,
            event_type="runbook.step",
            title=f"Runbook {step_key}: {payload.status}",
            severity=severity,
            actor_admin_id=admin_id,
            details={
                "step_key": step_key,
                "status": payload.status,
                "evidence_reference": step.evidence_reference,
            },
        )
        self.audit.add(
            action="launch.command.runbook.updated",
            actor_user_id=admin_id,
            entity_type="launch_runbook_step",
            entity_id=str(step.id),
            request_id=request_id,
            metadata={"step_key": step_key, "status": payload.status},
        )
        self.db.commit()
        self.db.refresh(step)
        return LaunchRunbookStepResponse.model_validate(step)

    def events(self, session_id: UUID, limit: int = 500) -> list[LaunchCommandEventResponse]:
        self._session(session_id)
        rows = list(
            self.db.scalars(
                select(LaunchCommandEventEntity)
                .where(LaunchCommandEventEntity.session_id == session_id)
                .order_by(LaunchCommandEventEntity.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [LaunchCommandEventResponse.model_validate(x) for x in rows]

    # ------------------------------------------------------------------
    # Traffic overrides
    # ------------------------------------------------------------------
    def create_override(
        self,
        *,
        session_id: UUID,
        payload: TrafficOverrideCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> TrafficOverrideResponse:
        session = self._require_active_session(session_id)
        if payload.duration_minutes > self.settings.launch_override_max_minutes:
            raise ApiError(
                422,
                "launch_override_too_long",
                "مدة الـTraffic Override أكبر من الحد المسموح.",
                {"max_minutes": self.settings.launch_override_max_minutes},
            )
        if payload.override_type not in {
            "daily_order_cap",
            "hourly_order_cap",
            "chef_daily_order_cap",
            "admission_enabled",
        }:
            raise ApiError(422, "launch_override_type_invalid", "نوع Traffic Override غير مدعوم.")

        active = self.db.scalar(
            select(LaunchTrafficOverrideEntity).where(
                LaunchTrafficOverrideEntity.zone_id == session.zone_id,
                LaunchTrafficOverrideEntity.override_type == payload.override_type,
                LaunchTrafficOverrideEntity.status == "active",
            )
        )
        if active is not None:
            raise ApiError(
                409,
                "launch_override_already_active",
                "يوجد Override نشط من نفس النوع.",
                {"override_id": str(active.id)},
            )

        zone = self._zone(session.zone_id)
        policy = self._policy(session.zone_id, lock=True)
        previous: int | bool | None

        if payload.override_type == "daily_order_cap":
            if isinstance(payload.value, bool) or int(payload.value) <= 0:
                raise ApiError(422, "launch_override_value_invalid", "Daily cap يجب أن يكون رقمًا موجبًا.")
            previous = zone.daily_order_cap
            value = int(payload.value)
            if previous is not None and value > previous:
                raise ApiError(409, "launch_override_cannot_increase_traffic", "Emergency override لا يمكنه زيادة Daily cap.")
            zone.daily_order_cap = value
        elif payload.override_type == "hourly_order_cap":
            if isinstance(payload.value, bool) or int(payload.value) <= 0:
                raise ApiError(422, "launch_override_value_invalid", "Hourly cap يجب أن يكون رقمًا موجبًا.")
            previous = policy.hourly_order_cap
            value = int(payload.value)
            if previous is not None and value > previous:
                raise ApiError(409, "launch_override_cannot_increase_traffic", "Emergency override لا يمكنه زيادة Hourly cap.")
            policy.hourly_order_cap = value
        elif payload.override_type == "chef_daily_order_cap":
            if isinstance(payload.value, bool) or int(payload.value) <= 0:
                raise ApiError(422, "launch_override_value_invalid", "Chef cap يجب أن يكون رقمًا موجبًا.")
            previous = policy.chef_daily_order_cap
            value = int(payload.value)
            if previous is not None and value > previous:
                raise ApiError(409, "launch_override_cannot_increase_traffic", "Emergency override لا يمكنه زيادة Chef cap.")
            policy.chef_daily_order_cap = value
        else:
            if payload.value is not False:
                raise ApiError(
                    409,
                    "launch_override_admission_only_disable",
                    "Emergency admission override يسمح بالإيقاف فقط؛ إعادة التشغيل تتم عبر Revert.",
                )
            previous = policy.is_enabled
            value = False
            policy.is_enabled = False

        row = LaunchTrafficOverrideEntity(
            session_id=session.id,
            zone_id=session.zone_id,
            override_type=payload.override_type,
            previous_value_json={"value": previous},
            override_value_json={"value": value},
            reason=payload.reason.strip(),
            status="active",
            expires_at=utc_now() + timedelta(minutes=payload.duration_minutes),
            activated_by_admin_id=admin_id,
        )
        self.db.add(row)
        self.db.flush()
        self._event(
            session_id=session.id,
            event_type="traffic.override.activated",
            title=f"Traffic override activated: {payload.override_type}",
            severity="warning",
            actor_admin_id=admin_id,
            details={
                "override_id": str(row.id),
                "previous": previous,
                "value": value,
                "expires_at": row.expires_at.isoformat(),
            },
        )
        self.audit.add(
            action="launch.command.traffic_override.activated",
            actor_user_id=admin_id,
            entity_type="launch_traffic_override",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"type": payload.override_type, "previous": previous, "value": value},
        )
        self.db.commit()
        self.db.refresh(row)
        return TrafficOverrideResponse.model_validate(row)

    def overrides(self, session_id: UUID) -> list[TrafficOverrideResponse]:
        self._session(session_id)
        rows = list(
            self.db.scalars(
                select(LaunchTrafficOverrideEntity)
                .where(LaunchTrafficOverrideEntity.session_id == session_id)
                .order_by(LaunchTrafficOverrideEntity.activated_at.desc())
            ).all()
        )
        return [TrafficOverrideResponse.model_validate(x) for x in rows]

    def _restore_override(
        self,
        row: LaunchTrafficOverrideEntity,
        *,
        reverted_by_admin_id: UUID | None,
        expired: bool,
    ) -> None:
        if row.status != "active":
            return
        zone = self._zone(row.zone_id)
        policy = self._policy(row.zone_id, lock=True)
        previous = row.previous_value_json.get("value")
        if row.override_type == "daily_order_cap":
            zone.daily_order_cap = previous
        elif row.override_type == "hourly_order_cap":
            policy.hourly_order_cap = previous
        elif row.override_type == "chef_daily_order_cap":
            policy.chef_daily_order_cap = previous
        elif row.override_type == "admission_enabled":
            policy.is_enabled = bool(previous)

        row.status = "expired" if expired else "reverted"
        row.reverted_by_admin_id = reverted_by_admin_id
        row.reverted_at = utc_now()
        self._event(
            session_id=row.session_id,
            event_type="traffic.override.expired" if expired else "traffic.override.reverted",
            title=f"Traffic override {'expired' if expired else 'reverted'}: {row.override_type}",
            severity="warning" if expired else "info",
            actor_admin_id=reverted_by_admin_id,
            details={"override_id": str(row.id), "restored": previous},
        )

    def revert_override(
        self,
        *,
        override_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> TrafficOverrideResponse:
        row = self.db.get(LaunchTrafficOverrideEntity, override_id)
        if row is None:
            raise ApiError(404, "launch_override_not_found", "Traffic Override غير موجود.")
        if row.status != "active":
            return TrafficOverrideResponse.model_validate(row)
        self._restore_override(row, reverted_by_admin_id=admin_id, expired=False)
        self.audit.add(
            action="launch.command.traffic_override.reverted",
            actor_user_id=admin_id,
            entity_type="launch_traffic_override",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return TrafficOverrideResponse.model_validate(row)

    def _revert_session_overrides(
        self,
        session_id: UUID,
        *,
        reverted_by_admin_id: UUID | None,
        expired: bool,
    ) -> int:
        rows = list(
            self.db.scalars(
                select(LaunchTrafficOverrideEntity).where(
                    LaunchTrafficOverrideEntity.session_id == session_id,
                    LaunchTrafficOverrideEntity.status == "active",
                )
            ).all()
        )
        for row in rows:
            self._restore_override(
                row,
                reverted_by_admin_id=reverted_by_admin_id,
                expired=expired,
            )
        return len(rows)

    def expire_overrides(self) -> int:
        now = utc_now()
        rows = list(
            self.db.scalars(
                select(LaunchTrafficOverrideEntity).where(
                    LaunchTrafficOverrideEntity.status == "active",
                    LaunchTrafficOverrideEntity.expires_at <= now,
                )
            ).all()
        )
        for row in rows:
            self._restore_override(row, reverted_by_admin_id=None, expired=True)
        if rows:
            self.db.commit()
        return len(rows)

    # ------------------------------------------------------------------
    # Daily financial close
    # ------------------------------------------------------------------
    def _orders_for_close(self, program: PilotProgramEntity, day: date) -> list[OrderEntity]:
        stmt = select(OrderEntity).where(OrderEntity.service_date == day)
        if program.area:
            stmt = (
                stmt.join(
                    OrderDeliveryAddressEntity,
                    OrderDeliveryAddressEntity.order_id == OrderEntity.id,
                )
                .where(OrderDeliveryAddressEntity.area == program.area)
            )
        return list(self.db.scalars(stmt).all())

    def prepare_financial_close(
        self,
        *,
        session_id: UUID,
        payload: FinancialClosePrepareRequest,
        admin_id: UUID | None,
        request_id: str | None,
        prepared_by_system: bool = False,
        cadence_due_at: datetime | None = None,
    ) -> DailyFinancialCloseResponse:
        session = self._session(session_id)
        allowed_statuses = {"active", "paused", "completed"} if prepared_by_system else {"active", "paused"}
        if session.status not in allowed_statuses:
            raise ApiError(409, "launch_session_not_operational", "الجلسة ليست مفتوحة.")
        if prepared_by_system:
            last_cadence_day = session.launch_date + timedelta(
                days=max(1, self.settings.launch_post_launch_stabilization_days) - 1
            )
            if payload.close_date < session.launch_date or payload.close_date > last_cadence_day:
                raise ApiError(
                    409,
                    "financial_close_outside_stabilization_window",
                    "تاريخ الإغلاق خارج نافذة الاستقرار بعد الإطلاق.",
                )
        program = self.db.get(PilotProgramEntity, session.pilot_program_id)
        if program is None:
            raise ApiError(404, "pilot_program_not_found", "برنامج الطيار غير موجود.")

        existing = self.db.scalar(
            select(DailyFinancialCloseEntity).where(
                DailyFinancialCloseEntity.session_id == session.id,
                DailyFinancialCloseEntity.close_date == payload.close_date,
            )
        )
        if existing is not None and existing.status == "closed":
            return DailyFinancialCloseResponse.model_validate(existing)

        orders = self._orders_for_close(program, payload.close_date)
        delivered = [x for x in orders if x.status == "delivered"]
        order_ids = {x.id for x in orders}
        delivered_ids = {x.id for x in delivered}

        payments = (
            list(
                self.db.scalars(
                    select(PaymentEntity).where(
                        PaymentEntity.order_id.in_(order_ids),
                        PaymentEntity.status == "succeeded",
                    )
                ).all()
            )
            if order_ids
            else []
        )
        refunds = (
            list(
                self.db.scalars(
                    select(RefundEntity).where(
                        RefundEntity.order_id.in_(order_ids),
                        RefundEntity.status == "succeeded",
                    )
                ).all()
            )
            if order_ids
            else []
        )
        payment_ids = {x.id for x in payments}
        paid_delivered = len({x.order_id for x in payments} & delivered_ids)

        cost_stmt = select(EconomicsCostEntryEntity).where(
            EconomicsCostEntryEntity.incurred_on == payload.close_date
        )
        if program.area:
            cost_stmt = cost_stmt.where(
                (EconomicsCostEntryEntity.pilot_program_id == program.id)
                | (
                    EconomicsCostEntryEntity.pilot_program_id.is_(None)
                    & (EconomicsCostEntryEntity.area == program.area)
                )
            )
        else:
            cost_stmt = cost_stmt.where(
                EconomicsCostEntryEntity.pilot_program_id == program.id
            )
        costs = list(self.db.scalars(cost_stmt).all())
        verified_costs = [x for x in costs if x.is_verified]
        unverified = len(costs) - len(verified_costs)

        required_types = [
            x.strip()
            for x in self.settings.economics_required_order_cost_types.split(",")
            if x.strip()
        ]
        types_by_order: dict[UUID, set[str]] = defaultdict(set)
        for row in verified_costs:
            if row.order_id in delivered_ids and row.cost_type in required_types:
                types_by_order[row.order_id].add(row.cost_type)
        fully_costed = sum(
            all(kind in types_by_order[order.id] for kind in required_types)
            for order in delivered
        )

        revenue_coverage = (
            round(paid_delivered / len(delivered) * 100, 2) if delivered else 100.0
        )
        cost_coverage = (
            round(fully_costed / len(delivered) * 100, 2) if delivered else 100.0
        )

        import_stmt = select(
            func.count(ProviderCostImportBatchEntity.id)
        ).where(
            ProviderCostImportBatchEntity.pilot_program_id == program.id,
            ProviderCostImportBatchEntity.period_start <= payload.close_date,
            ProviderCostImportBatchEntity.period_end >= payload.close_date,
            ProviderCostImportBatchEntity.status != "applied",
        )
        pending_imports = int(self.db.scalar(import_stmt) or 0)
        if self.settings.vendor_accounting_require_dual_control:
            pending_imports += int(
                self.db.scalar(
                    select(func.count(ProviderCostImportBatchEntity.id)).where(
                        ProviderCostImportBatchEntity.pilot_program_id == program.id,
                        ProviderCostImportBatchEntity.period_start <= payload.close_date,
                        ProviderCostImportBatchEntity.period_end >= payload.close_date,
                        ProviderCostImportBatchEntity.status == "applied",
                        ProviderCostImportBatchEntity.review_status != "approved",
                    )
                )
                or 0
            )
        unclosed_settlements = int(
            self.db.scalar(
                select(func.count(ProviderSettlementBatchEntity.id)).where(
                    ProviderSettlementBatchEntity.pilot_program_id == program.id,
                    ProviderSettlementBatchEntity.period_start <= payload.close_date,
                    ProviderSettlementBatchEntity.period_end >= payload.close_date,
                    ProviderSettlementBatchEntity.operations_status != "closed",
                )
            )
            or 0
        )
        open_payment_issues = (
            int(
                self.db.scalar(
                    select(func.count(PaymentReconciliationIssueEntity.id)).where(
                        PaymentReconciliationIssueEntity.payment_id.in_(payment_ids),
                        PaymentReconciliationIssueEntity.status == "open",
                    )
                )
                or 0
            )
            if payment_ids
            else 0
        )

        captured = sum(x.amount_minor for x in payments)
        refunded = sum(x.amount_minor for x in refunds)
        net = captured - refunded
        variable = sum(x.amount_minor for x in verified_costs if x.cost_scope == "variable")
        fixed = sum(x.amount_minor for x in verified_costs if x.cost_scope == "fixed")
        contribution = net - variable
        operational_profit = contribution - fixed

        blockers: list[str] = []
        if revenue_coverage < 100:
            blockers.append("revenue_coverage_below_100_pct")
        if cost_coverage < 100:
            blockers.append("cost_coverage_below_100_pct")
        if unverified:
            blockers.append("unverified_cost_entries")
        if pending_imports:
            blockers.append("pending_provider_imports")
        if unclosed_settlements:
            blockers.append("unclosed_provider_settlements")
        if open_payment_issues:
            blockers.append("open_payment_reconciliation_issues")

        summary = {
            "date": payload.close_date.isoformat(),
            "delivered_orders": len(delivered),
            "captured_minor": captured,
            "refunded_minor": refunded,
            "net_collected_minor": net,
            "variable_cost_minor": variable,
            "fixed_cost_minor": fixed,
            "verified_cost_minor": variable + fixed,
            "contribution_minor": contribution,
            "operational_profit_minor": operational_profit,
            "revenue_coverage_pct": revenue_coverage,
            "cost_coverage_pct": cost_coverage,
            "required_cost_types": required_types,
            "pending_provider_imports": pending_imports,
            "unclosed_settlements": unclosed_settlements,
            "open_payment_issues": open_payment_issues,
        }

        if existing is None:
            row = DailyFinancialCloseEntity(
                session_id=session.id,
                pilot_program_id=program.id,
                close_date=payload.close_date,
                prepared_by_admin_id=admin_id,
                prepared_by_system=prepared_by_system,
                cadence_due_at=cadence_due_at,
            )
            self.db.add(row)
        else:
            row = existing
            row.prepared_by_admin_id = admin_id
            row.prepared_by_system = prepared_by_system
            row.prepared_at = utc_now()
            if cadence_due_at is not None:
                row.cadence_due_at = cadence_due_at

        row.status = "ready" if not blockers else "blocked"
        row.delivered_orders = len(delivered)
        row.succeeded_payment_orders = paid_delivered
        row.captured_minor = captured
        row.refunded_minor = refunded
        row.net_collected_minor = net
        row.verified_cost_minor = variable + fixed
        row.contribution_minor = contribution
        row.operational_profit_minor = operational_profit
        row.revenue_coverage_pct = revenue_coverage
        row.cost_coverage_pct = cost_coverage
        row.unverified_cost_entries = unverified
        row.pending_provider_imports = pending_imports
        row.unclosed_settlements = unclosed_settlements
        row.open_payment_issues = open_payment_issues
        row.blockers_json = blockers
        row.summary_json = summary
        row.checksum_sha256 = None
        row.closed_by_admin_id = None
        row.closed_at = None
        row.note = payload.note
        self.db.flush()

        self._event(
            session_id=session.id,
            event_type="finance.close.prepared",
            title=f"Daily financial close prepared: {payload.close_date}",
            severity="high" if blockers else "info",
            actor_admin_id=admin_id,
            details={"close_id": str(row.id), "status": row.status, "blockers": blockers, "prepared_by_system": prepared_by_system},
        )
        self.audit.add(
            action="launch.command.financial_close.prepared",
            actor_user_id=admin_id,
            entity_type="daily_financial_close",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"date": payload.close_date.isoformat(), "blockers": blockers, "prepared_by_system": prepared_by_system},
        )
        self.db.commit()
        self.db.refresh(row)
        return DailyFinancialCloseResponse.model_validate(row)

    def financial_closes(self, session_id: UUID) -> list[DailyFinancialCloseResponse]:
        self._session(session_id)
        rows = list(
            self.db.scalars(
                select(DailyFinancialCloseEntity)
                .where(DailyFinancialCloseEntity.session_id == session_id)
                .order_by(DailyFinancialCloseEntity.close_date.desc())
            ).all()
        )
        return [DailyFinancialCloseResponse.model_validate(x) for x in rows]

    def close_financial_day(
        self,
        *,
        close_id: UUID,
        payload: FinancialCloseActionRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> DailyFinancialCloseResponse:
        row = self.db.get(DailyFinancialCloseEntity, close_id)
        if row is None:
            raise ApiError(404, "daily_financial_close_not_found", "Daily Financial Close غير موجود.")
        if row.status != "ready":
            raise ApiError(
                409,
                "daily_financial_close_not_ready",
                "لا يمكن غلق اليوم قبل إزالة كل blockers.",
                {"blockers": row.blockers_json},
            )
        if (
            self.settings.launch_command_require_dual_control
            and not row.prepared_by_system
            and row.prepared_by_admin_id == admin_id
        ):
            raise ApiError(
                409,
                "launch_dual_control_required",
                "مُعدّ الإغلاق اليومي لا يمكنه إغلاقه في وضع maker-checker.",
            )
        canonical = json.dumps(row.summary_json, sort_keys=True, separators=(",", ":"))
        row.checksum_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        row.status = "closed"
        row.closed_by_admin_id = admin_id
        row.closed_at = utc_now()
        row.reopened_by_admin_id = None
        row.reopened_at = None
        row.note = payload.note.strip()

        self._event(
            session_id=row.session_id,
            event_type="finance.close.closed",
            title=f"Daily financial close CLOSED: {row.close_date}",
            actor_admin_id=admin_id,
            details={"close_id": str(row.id), "checksum": row.checksum_sha256},
        )
        self.audit.add(
            action="launch.command.financial_close.closed",
            actor_user_id=admin_id,
            entity_type="daily_financial_close",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"checksum": row.checksum_sha256},
        )
        self.db.commit()
        self.db.refresh(row)
        return DailyFinancialCloseResponse.model_validate(row)

    def reopen_financial_day(
        self,
        *,
        close_id: UUID,
        payload: FinancialCloseActionRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> DailyFinancialCloseResponse:
        row = self.db.get(DailyFinancialCloseEntity, close_id)
        if row is None:
            raise ApiError(404, "daily_financial_close_not_found", "Daily Financial Close غير موجود.")
        if row.status != "closed":
            raise ApiError(409, "daily_financial_close_not_closed", "يمكن إعادة فتح يوم Closed فقط.")
        row.status = "reopened"
        row.reopened_by_admin_id = admin_id
        row.reopened_at = utc_now()
        row.closed_by_admin_id = None
        row.closed_at = None
        row.checksum_sha256 = None
        row.note = payload.note.strip()
        self._event(
            session_id=row.session_id,
            event_type="finance.close.reopened",
            title=f"Daily financial close reopened: {row.close_date}",
            severity="warning",
            actor_admin_id=admin_id,
        )
        self.audit.add(
            action="launch.command.financial_close.reopened",
            actor_user_id=admin_id,
            entity_type="daily_financial_close",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return DailyFinancialCloseResponse.model_validate(row)

    # ------------------------------------------------------------------
    # Rollback drills
    # ------------------------------------------------------------------
    def start_rollback_drill(
        self,
        *,
        session_id: UUID,
        payload: RollbackDrillCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> RollbackDrillResponse:
        session = self._require_active_session(session_id)
        running = self.db.scalar(
            select(LaunchRollbackDrillEntity).where(
                LaunchRollbackDrillEntity.session_id == session.id,
                LaunchRollbackDrillEntity.status == "running",
            )
        )
        if running is not None:
            raise ApiError(409, "rollback_drill_already_running", "يوجد Rollback Drill قيد التنفيذ.")

        zone = self._zone(session.zone_id)
        policy = self._policy(session.zone_id, lock=True)
        pre_state = {
            "zone_status": zone.status,
            "rollout_stage": zone.rollout_stage,
            "rollout_percent": zone.rollout_percent,
            "daily_order_cap": zone.daily_order_cap,
            "admission_enabled": policy.is_enabled,
            "hourly_order_cap": policy.hourly_order_cap,
            "chef_daily_order_cap": policy.chef_daily_order_cap,
        }

        if payload.mode == "live_controlled":
            active_stop = self.db.scalar(
                select(LaunchTrafficOverrideEntity).where(
                    LaunchTrafficOverrideEntity.zone_id == zone.id,
                    LaunchTrafficOverrideEntity.override_type == "admission_enabled",
                    LaunchTrafficOverrideEntity.status == "active",
                )
            )
            if active_stop is not None:
                raise ApiError(
                    409,
                    "rollback_drill_conflicts_with_override",
                    "يوجد admission override نشط بالفعل.",
                )
            policy.is_enabled = False

        row = LaunchRollbackDrillEntity(
            session_id=session.id,
            zone_id=zone.id,
            mode=payload.mode,
            status="running",
            target_recovery_seconds=(
                payload.target_recovery_seconds
                or self.settings.launch_rollback_target_seconds
            ),
            pre_state_json=pre_state,
            result_json={},
            note=payload.note,
            initiated_by_admin_id=admin_id,
        )
        self.db.add(row)
        self.db.flush()
        self._event(
            session_id=session.id,
            event_type="rollback.drill.started",
            title=f"Rollback drill started: {payload.mode}",
            severity="warning",
            actor_admin_id=admin_id,
            details={"drill_id": str(row.id), "target_seconds": row.target_recovery_seconds},
        )
        self.audit.add(
            action="launch.command.rollback_drill.started",
            actor_user_id=admin_id,
            entity_type="launch_rollback_drill",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"mode": payload.mode},
        )
        self.db.commit()
        self.db.refresh(row)
        return RollbackDrillResponse.model_validate(row)

    def _restore_drill_policy(self, drill: LaunchRollbackDrillEntity) -> None:
        if drill.mode != "live_controlled":
            return
        policy = self._policy(drill.zone_id, lock=True)
        policy.is_enabled = bool(drill.pre_state_json.get("admission_enabled", True))

    def complete_rollback_drill(
        self,
        *,
        drill_id: UUID,
        payload: RollbackDrillComplete,
        admin_id: UUID,
        request_id: str | None,
    ) -> RollbackDrillResponse:
        row = self.db.get(LaunchRollbackDrillEntity, drill_id)
        if row is None:
            raise ApiError(404, "rollback_drill_not_found", "Rollback Drill غير موجود.")
        if row.status != "running":
            return RollbackDrillResponse.model_validate(row)
        if (
            self.settings.launch_command_require_dual_control
            and row.initiated_by_admin_id == admin_id
        ):
            raise ApiError(
                409,
                "launch_dual_control_required",
                "من بدأ Rollback Drill لا يمكنه التحقق النهائي منه.",
            )

        self._restore_drill_policy(row)
        now = utc_now()
        recovery_seconds = max(
            0,
            int((now - ensure_utc(row.started_at)).total_seconds()),
        )
        passed = bool(payload.passed) and recovery_seconds <= row.target_recovery_seconds
        row.status = "passed" if passed else "failed"
        row.recovery_seconds = recovery_seconds
        row.evidence_reference = payload.evidence_reference.strip()
        row.note = payload.note
        row.verified_by_admin_id = admin_id
        row.completed_at = now
        row.result_json = {
            "operator_passed": bool(payload.passed),
            "within_target": recovery_seconds <= row.target_recovery_seconds,
            "recovery_seconds": recovery_seconds,
            "target_recovery_seconds": row.target_recovery_seconds,
            "admission_restored": True,
        }
        self._event(
            session_id=row.session_id,
            event_type="rollback.drill.completed",
            title=f"Rollback drill {row.status}",
            severity="info" if passed else "critical",
            actor_admin_id=admin_id,
            details={"drill_id": str(row.id), **row.result_json},
        )
        self.audit.add(
            action="launch.command.rollback_drill.completed",
            actor_user_id=admin_id,
            entity_type="launch_rollback_drill",
            entity_id=str(row.id),
            request_id=request_id,
            metadata=row.result_json,
        )
        self.db.commit()
        self.db.refresh(row)
        return RollbackDrillResponse.model_validate(row)

    def rollback_drills(self, session_id: UUID) -> list[RollbackDrillResponse]:
        self._session(session_id)
        rows = list(
            self.db.scalars(
                select(LaunchRollbackDrillEntity)
                .where(LaunchRollbackDrillEntity.session_id == session_id)
                .order_by(LaunchRollbackDrillEntity.started_at.desc())
            ).all()
        )
        return [RollbackDrillResponse.model_validate(x) for x in rows]

    def _recover_running_drills(
        self,
        session_id: UUID | None = None,
        *,
        actor_admin_id: UUID | None = None,
        force_abort: bool = False,
    ) -> int:
        stmt = select(LaunchRollbackDrillEntity).where(
            LaunchRollbackDrillEntity.status == "running"
        )
        if session_id:
            stmt = stmt.where(LaunchRollbackDrillEntity.session_id == session_id)
        rows = list(self.db.scalars(stmt).all())
        recovered = 0
        now = utc_now()
        for row in rows:
            age = int((now - ensure_utc(row.started_at)).total_seconds())
            if not force_abort and age <= row.target_recovery_seconds:
                continue
            self._restore_drill_policy(row)
            row.status = "aborted"
            row.recovery_seconds = age
            row.completed_at = now
            row.result_json = {
                "auto_recovered": True,
                "reason": "drill_timeout" if not force_abort else "session_abort",
                "admission_restored": True,
            }
            self._event(
                session_id=row.session_id,
                event_type="rollback.drill.auto_recovered",
                title="Rollback drill auto-recovered",
                severity="critical",
                actor_admin_id=actor_admin_id,
                details={"drill_id": str(row.id), **row.result_json},
            )
            recovered += 1
        return recovered

    # ------------------------------------------------------------------
    # Evidence pack / command state
    # ------------------------------------------------------------------
    def evidence_packs(self, session_id: UUID) -> list[EvidencePackResponse]:
        self._session(session_id)
        rows = list(
            self.db.scalars(
                select(LaunchEvidencePackEntity)
                .where(LaunchEvidencePackEntity.session_id == session_id)
                .order_by(LaunchEvidencePackEntity.generated_at.desc())
            ).all()
        )
        return [EvidencePackResponse.model_validate(x) for x in rows]

    def generate_evidence_pack(
        self,
        *,
        session_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> EvidencePackResponse:
        session = self._session(session_id)
        zone = self._zone(session.zone_id)
        policy = self._policy(zone.id)

        steps = list(
            self.db.scalars(
                select(LaunchRunbookStepEntity).where(
                    LaunchRunbookStepEntity.session_id == session.id
                )
            ).all()
        )
        required_not_passed = [
            x.step_key for x in steps if x.is_required and x.status != "passed"
        ]

        monitoring = self.db.scalar(
            select(ExpansionMonitoringSnapshotEntity)
            .where(ExpansionMonitoringSnapshotEntity.zone_id == zone.id)
            .order_by(ExpansionMonitoringSnapshotEntity.observed_at.desc())
            .limit(1)
        )
        close = self.db.scalar(
            select(DailyFinancialCloseEntity)
            .where(
                DailyFinancialCloseEntity.session_id == session.id,
                DailyFinancialCloseEntity.close_date == session.launch_date,
            )
            .order_by(DailyFinancialCloseEntity.updated_at.desc())
            .limit(1)
        )
        drill = self.db.scalar(
            select(LaunchRollbackDrillEntity)
            .where(
                LaunchRollbackDrillEntity.session_id == session.id,
                LaunchRollbackDrillEntity.status == "passed",
            )
            .order_by(LaunchRollbackDrillEntity.completed_at.desc())
            .limit(1)
        )
        active_overrides = list(
            self.db.scalars(
                select(LaunchTrafficOverrideEntity).where(
                    LaunchTrafficOverrideEntity.session_id == session.id,
                    LaunchTrafficOverrideEntity.status == "active",
                )
            ).all()
        )
        applied_reviewed_imports = int(
            self.db.scalar(
                select(func.count(ProviderCostImportBatchEntity.id)).where(
                    ProviderCostImportBatchEntity.pilot_program_id == session.pilot_program_id,
                    ProviderCostImportBatchEntity.status == "applied",
                    ProviderCostImportBatchEntity.review_status == "approved",
                )
            )
            or 0
        )
        closed_settlements = int(
            self.db.scalar(
                select(func.count(ProviderSettlementBatchEntity.id)).where(
                    ProviderSettlementBatchEntity.pilot_program_id == session.pilot_program_id,
                    ProviderSettlementBatchEntity.status == "reconciled",
                    ProviderSettlementBatchEntity.operations_status == "closed",
                )
            )
            or 0
        )
        unclosed_settlements = int(
            self.db.scalar(
                select(func.count(ProviderSettlementBatchEntity.id)).where(
                    ProviderSettlementBatchEntity.pilot_program_id == session.pilot_program_id,
                    ProviderSettlementBatchEntity.operations_status != "closed",
                )
            )
            or 0
        )
        critical_incidents = int(
            self.db.scalar(
                select(func.count(OperationsIncidentEntity.id)).where(
                    OperationsIncidentEntity.source_id == str(zone.id),
                    OperationsIncidentEntity.status.in_(["open", "acknowledged"]),
                    OperationsIncidentEntity.severity == "critical",
                )
            )
            or 0
        )

        blockers: list[str] = []
        if session.status not in {"active", "paused", "completed"}:
            blockers.append("launch_session_not_operational")
        if required_not_passed:
            blockers.append("required_runbook_steps_not_passed")
        if monitoring is None:
            blockers.append("expansion_monitoring_missing")
        elif monitoring.health == "red":
            blockers.append("expansion_monitoring_red")
        if close is None or close.status != "closed":
            blockers.append("launch_day_financial_close_not_closed")
        if drill is None:
            blockers.append("rollback_drill_not_passed")
        if self.settings.launch_evidence_require_no_active_overrides and active_overrides:
            blockers.append("active_traffic_overrides_present")
        if applied_reviewed_imports <= 0:
            blockers.append("approved_applied_provider_import_missing")
        if closed_settlements <= 0:
            blockers.append("closed_provider_settlement_missing")
        if unclosed_settlements:
            blockers.append("unclosed_provider_settlements")
        if critical_incidents:
            blockers.append("critical_zone_incidents_open")
        if zone.status not in {"live", "paused"} or zone.rollout_stage not in {
            "canary", "limited", "full", "paused"
        }:
            blockers.append("zone_rollout_not_started")
        if not policy.is_enabled and zone.status == "live":
            blockers.append("admission_policy_disabled")
        if session.finance_admin_id is None or session.operations_admin_id is None:
            blockers.append("launch_roles_incomplete")

        evidence = {
            "release": {
                "version": self.settings.release_version,
                "migration_head": MIGRATION_HEAD,
                "commit": self.settings.release_commit,
            },
            "session": LaunchSessionResponse.model_validate(session).model_dump(mode="json"),
            "zone": {
                "zone_id": str(zone.id),
                "status": zone.status,
                "rollout_stage": zone.rollout_stage,
                "rollout_percent": zone.rollout_percent,
                "daily_order_cap": zone.daily_order_cap,
                "traffic_policy_enabled": policy.is_enabled,
                "hourly_order_cap": policy.hourly_order_cap,
                "chef_daily_order_cap": policy.chef_daily_order_cap,
            },
            "runbook": {
                "total": len(steps),
                "required_not_passed": required_not_passed,
                "passed": sum(x.status == "passed" for x in steps),
            },
            "monitoring": (
                {
                    "id": str(monitoring.id),
                    "health": monitoring.health,
                    "blockers": monitoring.blockers_json,
                    "observed_at": monitoring.observed_at.isoformat(),
                }
                if monitoring
                else None
            ),
            "daily_financial_close": (
                {
                    "id": str(close.id),
                    "status": close.status,
                    "checksum_sha256": close.checksum_sha256,
                    "operational_profit_minor": close.operational_profit_minor,
                }
                if close
                else None
            ),
            "rollback_drill": (
                {
                    "id": str(drill.id),
                    "status": drill.status,
                    "recovery_seconds": drill.recovery_seconds,
                    "target_recovery_seconds": drill.target_recovery_seconds,
                    "evidence_reference": drill.evidence_reference,
                }
                if drill
                else None
            ),
            "traffic_overrides": {
                "active_count": len(active_overrides),
                "active_ids": [str(x.id) for x in active_overrides],
            },
            "vendor_accounting": {
                "approved_applied_imports": applied_reviewed_imports,
                "closed_settlements": closed_settlements,
                "unclosed_settlements": unclosed_settlements,
            },
            "critical_zone_incidents": critical_incidents,
        }
        canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        pack_status = "complete" if not blockers else "incomplete"
        generated_at = utc_now()
        row = LaunchEvidencePackEntity(
            session_id=session.id,
            status=pack_status,
            release_version=self.settings.release_version,
            migration_head=MIGRATION_HEAD,
            evidence_json=evidence,
            blockers_json=blockers,
            checksum_sha256=checksum,
            generated_by_admin_id=admin_id,
            retention_class="final" if pack_status == "complete" else "working",
            retain_until=(
                None
                if pack_status == "complete"
                else generated_at + timedelta(days=self.settings.launch_incomplete_evidence_retention_days)
            ),
            generated_at=generated_at,
        )
        self.db.add(row)
        self.db.flush()
        self._event(
            session_id=session.id,
            event_type="evidence.pack.generated",
            title=f"Launch evidence pack: {row.status}",
            severity="info" if not blockers else "high",
            actor_admin_id=admin_id,
            details={"pack_id": str(row.id), "blockers": blockers, "checksum": checksum},
        )
        self.audit.add(
            action="launch.command.evidence_pack.generated",
            actor_user_id=admin_id,
            entity_type="launch_evidence_pack",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"status": row.status, "blockers": blockers},
        )
        self.db.commit()
        self.db.refresh(row)
        return EvidencePackResponse.model_validate(row)

    def overview(self, session_id: UUID) -> LaunchCommandOverview:
        session = self._session(session_id)
        zone = self._zone(session.zone_id)
        steps = list(
            self.db.scalars(
                select(LaunchRunbookStepEntity).where(
                    LaunchRunbookStepEntity.session_id == session.id
                )
            ).all()
        )
        active_overrides = int(
            self.db.scalar(
                select(func.count(LaunchTrafficOverrideEntity.id)).where(
                    LaunchTrafficOverrideEntity.session_id == session.id,
                    LaunchTrafficOverrideEntity.status == "active",
                )
            )
            or 0
        )
        close = self.db.scalar(
            select(DailyFinancialCloseEntity)
            .where(DailyFinancialCloseEntity.session_id == session.id)
            .order_by(DailyFinancialCloseEntity.close_date.desc())
            .limit(1)
        )
        drill = self.db.scalar(
            select(LaunchRollbackDrillEntity)
            .where(LaunchRollbackDrillEntity.session_id == session.id)
            .order_by(LaunchRollbackDrillEntity.started_at.desc())
            .limit(1)
        )
        pack = self.db.scalar(
            select(LaunchEvidencePackEntity)
            .where(LaunchEvidencePackEntity.session_id == session.id)
            .order_by(LaunchEvidencePackEntity.generated_at.desc())
            .limit(1)
        )
        blocking = sum(
            x.is_required and x.status != "passed"
            for x in steps
        )
        return LaunchCommandOverview(
            session=LaunchSessionResponse.model_validate(session),
            zone_status=zone.status,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            runbook_total=len(steps),
            runbook_passed=sum(x.status == "passed" for x in steps),
            runbook_blocking=blocking,
            active_overrides=active_overrides,
            latest_financial_close=(
                DailyFinancialCloseResponse.model_validate(close) if close else None
            ),
            latest_rollback_drill=(
                RollbackDrillResponse.model_validate(drill) if drill else None
            ),
            latest_evidence_pack=(
                EvidencePackResponse.model_validate(pack) if pack else None
            ),
        )

    def complete_session(
        self,
        *,
        session_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> LaunchSessionResponse:
        row = self._session(session_id, lock=True)
        if row.status not in {"active", "paused"}:
            raise ApiError(409, "launch_session_not_completable", "الجلسة ليست قابلة للإغلاق.")
        pack = self.db.scalar(
            select(LaunchEvidencePackEntity)
            .where(LaunchEvidencePackEntity.session_id == row.id)
            .order_by(LaunchEvidencePackEntity.generated_at.desc())
            .limit(1)
        )
        if pack is None or pack.status != "complete":
            raise ApiError(
                409,
                "launch_evidence_pack_incomplete",
                "لا يمكن إغلاق Launch Command قبل Evidence Pack كاملة.",
                {"blockers": pack.blockers_json if pack else ["evidence_pack_missing"]},
            )
        row.status = "completed"
        row.completed_at = utc_now()
        row.paused_at = None
        self._event(
            session_id=row.id,
            event_type="session.completed",
            title="Launch command completed",
            actor_admin_id=admin_id,
            details={"evidence_pack_id": str(pack.id), "checksum": pack.checksum_sha256},
        )
        self.audit.add(
            action="launch.command.session.completed",
            actor_user_id=admin_id,
            entity_type="launch_command_session",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"evidence_pack_id": str(pack.id)},
        )
        self.db.commit()
        self.db.refresh(row)
        return LaunchSessionResponse.model_validate(row)

    # ------------------------------------------------------------------
    # Worker maintenance
    # ------------------------------------------------------------------
    def _cadence_prepare_at(self, close_date: date) -> datetime:
        """Earliest safe time to prepare a completed service day."""
        return datetime.combine(
            close_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

    def _cadence_due_at(self, close_date: date) -> datetime:
        """Operational close deadline; grace is not the preparation trigger."""
        return self._cadence_prepare_at(close_date) + timedelta(
            hours=self.settings.launch_financial_close_grace_hours
        )

    def prepare_due_financial_closes(self) -> int:
        """Create one system-prepared close per due service day during stabilization.

        The existing DailyFinancialClose ledger remains canonical. This job is
        creation-only/idempotent; it never auto-closes a day and never rewrites
        a human-prepared or already-closed close.
        """
        if not self.settings.launch_daily_close_cadence_enabled:
            return 0
        now = utc_now()
        sessions = list(
            self.db.scalars(
                select(LaunchCommandSessionEntity).where(
                    LaunchCommandSessionEntity.status.in_(["active", "paused", "completed"]),
                    LaunchCommandSessionEntity.launch_date <= now.date(),
                )
            ).all()
        )
        created = 0
        for session in sessions:
            last_day = session.launch_date + timedelta(
                days=max(1, self.settings.launch_post_launch_stabilization_days) - 1
            )
            day = session.launch_date
            while day <= min(last_day, now.date()):
                prepare_at = self._cadence_prepare_at(day)
                due_at = self._cadence_due_at(day)
                if prepare_at > now:
                    day += timedelta(days=1)
                    continue
                existing = self.db.scalar(
                    select(DailyFinancialCloseEntity).where(
                        DailyFinancialCloseEntity.session_id == session.id,
                        DailyFinancialCloseEntity.close_date == day,
                    )
                )
                if existing is None:
                    self.prepare_financial_close(
                        session_id=session.id,
                        payload=FinancialClosePrepareRequest(
                            close_date=day,
                            note="system_cadence",
                        ),
                        admin_id=None,
                        request_id=None,
                        prepared_by_system=True,
                        cadence_due_at=due_at,
                    )
                    created += 1
                elif existing.cadence_due_at is None:
                    existing.cadence_due_at = due_at
                    self.db.commit()
                day += timedelta(days=1)
        return created

    def monitor_overdue_financial_closes(self) -> int:
        now = utc_now()
        created = 0

        # Sprint 50 cadence rows are self-identifying and can emit one durable
        # overdue event per close without JSON-query tricks or duplicate events.
        cadence_rows = list(
            self.db.scalars(
                select(DailyFinancialCloseEntity).where(
                    DailyFinancialCloseEntity.cadence_due_at.is_not(None),
                    DailyFinancialCloseEntity.cadence_due_at <= now,
                    DailyFinancialCloseEntity.status != "closed",
                    DailyFinancialCloseEntity.overdue_notified_at.is_(None),
                )
            ).all()
        )
        for row in cadence_rows:
            row.overdue_notified_at = now
            self._event(
                session_id=row.session_id,
                event_type="finance.close.overdue",
                title=f"Daily financial close overdue: {row.close_date}",
                severity="high",
                details={"close_id": str(row.id), "close_date": row.close_date.isoformat()},
            )
            created += 1

        # Preserve Sprint 49 launch-day overdue behavior when cadence is disabled
        # or a historical session predates cadence metadata.
        cutoff = now - timedelta(hours=self.settings.launch_financial_close_grace_hours)
        sessions = list(
            self.db.scalars(
                select(LaunchCommandSessionEntity).where(
                    LaunchCommandSessionEntity.status.in_(["active", "paused"]),
                    LaunchCommandSessionEntity.launch_date < now.date(),
                )
            ).all()
        )
        for session in sessions:
            any_close = self.db.scalar(
                select(DailyFinancialCloseEntity).where(
                    DailyFinancialCloseEntity.session_id == session.id,
                    DailyFinancialCloseEntity.close_date == session.launch_date,
                )
            )
            if any_close is not None:
                continue
            existing = self.db.scalar(
                select(LaunchCommandEventEntity).where(
                    LaunchCommandEventEntity.session_id == session.id,
                    LaunchCommandEventEntity.event_type == "finance.close.overdue",
                )
            )
            if existing is None and datetime.combine(
                session.launch_date + timedelta(days=1),
                time.min,
                tzinfo=timezone.utc,
            ) <= cutoff:
                self._event(
                    session_id=session.id,
                    event_type="finance.close.overdue",
                    title="Launch-day financial close overdue",
                    severity="high",
                    details={"launch_date": session.launch_date.isoformat()},
                )
                created += 1
        if created:
            self.db.commit()
        return created

    def prune_expired_working_evidence(self) -> int:
        """Prune only superseded incomplete packs after their retention date.

        Complete/final evidence is never automatically deleted, and the newest
        pack for a session is always retained even if incomplete.
        """
        now = utc_now()
        rows = list(
            self.db.scalars(
                select(LaunchEvidencePackEntity).where(
                    LaunchEvidencePackEntity.status == "incomplete",
                    LaunchEvidencePackEntity.retention_class == "working",
                    LaunchEvidencePackEntity.retain_until.is_not(None),
                    LaunchEvidencePackEntity.retain_until <= now,
                )
            ).all()
        )
        deleted = 0
        for row in rows:
            newer = self.db.scalar(
                select(LaunchEvidencePackEntity.id)
                .where(
                    LaunchEvidencePackEntity.session_id == row.session_id,
                    LaunchEvidencePackEntity.generated_at > row.generated_at,
                )
                .limit(1)
            )
            if newer is None:
                continue
            self.db.delete(row)
            deleted += 1
        if deleted:
            self.db.commit()
        return deleted

    def maintain(self) -> dict:
        expired = self.expire_overrides()
        recovered = self._recover_running_drills()
        cadence_created = self.prepare_due_financial_closes()
        overdue = self.monitor_overdue_financial_closes()
        pruned = self.prune_expired_working_evidence()
        if recovered:
            self.db.commit()
        # Expansion review is imported lazily to avoid a module cycle.
        from app.modules.post_launch.service import PostLaunchStabilizationService

        reviews = PostLaunchStabilizationService(
            self.db, self.settings
        ).refresh_due_reviews()
        return {
            "expired_overrides": expired,
            "auto_recovered_drills": recovered,
            "daily_closes_prepared": cadence_created,
            "overdue_financial_close_events": overdue,
            "working_evidence_pruned": pruned,
            "expansion_reviews_created": reviews,
        }
