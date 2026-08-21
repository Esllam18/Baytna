from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    BackgroundJobEntity,
    ChefOrderFulfillmentEntity,
    ChefProfileEntity,
    DeliveryTaskEntity,
    DriverProfileEntity,
    ExpansionMonitoringSnapshotEntity,
    ExpansionZoneEntity,
    NotificationDeliveryEntity,
    OperationsIncidentEntity,
    OrderEntity,
    OutboxEventEntity,
    PaymentReconciliationIssueEntity,
    ProviderSettlementBatchEntity,
    ReviewEntity,
    SupportTicketEntity,
    UserEntity,
    WorkerHeartbeatEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.analytics.service import AnalyticsService
from app.modules.notifications.service import NotificationService
from app.modules.operations_control.schemas import (
    ControlRoomOverview,
    DailyActionItem,
    DailyBrief,
    IncidentRefreshResponse,
    IncidentResponse,
    LaunchKpis,
)

OPEN_SUPPORT = {
    "new",
    "assigned",
    "investigating",
    "awaiting_customer",
    "awaiting_internal",
}
ACTIVE_INCIDENT = {"open", "acknowledged"}
SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "warning": 2,
    "info": 3,
}


@dataclass(frozen=True)
class AlertCandidate:
    fingerprint: str
    category: str
    severity: str
    source_type: str
    source_id: str | None
    title: str
    message: str
    details: dict


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _minutes_between(start: datetime, end: datetime) -> int:
    seconds = max(0.0, (_aware(end) - _aware(start)).total_seconds())
    return int(seconds // 60)


class OperationsControlService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    def _support_sla_minutes(self, priority: str) -> int:
        if priority == "urgent":
            return self.settings.ops_support_urgent_sla_minutes
        if priority == "high":
            return self.settings.ops_support_high_sla_minutes
        return self.settings.ops_support_normal_sla_minutes

    def detect_candidates(self) -> list[AlertCandidate]:
        now = utc_now()
        candidates: list[AlertCandidate] = []

        # Chef acceptance SLA.
        chef_rows = list(
            self.db.scalars(
                select(ChefOrderFulfillmentEntity).where(
                    ChefOrderFulfillmentEntity.stage == "new",
                    ChefOrderFulfillmentEntity.acceptance_deadline_at.is_not(None),
                    ChefOrderFulfillmentEntity.acceptance_deadline_at < now,
                )
            ).all()
        )
        for row in chef_rows:
            deadline = _aware(row.acceptance_deadline_at)
            overdue = _minutes_between(deadline, now)
            severity = (
                "critical"
                if overdue >= max(10, self.settings.chef_acceptance_sla_minutes)
                else "high"
            )
            candidates.append(
                AlertCandidate(
                    fingerprint=f"chef_acceptance:{row.order_id}",
                    category="chef_sla",
                    severity=severity,
                    source_type="order",
                    source_id=str(row.order_id),
                    title="تأخر قبول الشيف للطلب",
                    message=(
                        f"الطلب تجاوز مهلة قبول الشيف بحوالي {overdue} دقيقة."
                    ),
                    details={
                        "order_id": str(row.order_id),
                        "chef_id": str(row.chef_id),
                        "overdue_minutes": overdue,
                        "deadline": deadline.isoformat(),
                    },
                )
            )

        # Driver assignment SLA.
        assignment_cutoff = now - timedelta(
            minutes=self.settings.ops_delivery_assignment_sla_minutes
        )
        delivery_rows = list(
            self.db.scalars(
                select(DeliveryTaskEntity).where(
                    DeliveryTaskEntity.status == "unassigned",
                    DeliveryTaskEntity.created_at < assignment_cutoff,
                )
            ).all()
        )
        for row in delivery_rows:
            age = _minutes_between(row.created_at, now)
            severity = (
                "critical"
                if age >= self.settings.ops_delivery_assignment_sla_minutes * 2
                else "high"
            )
            candidates.append(
                AlertCandidate(
                    fingerprint=f"delivery_assignment:{row.id}",
                    category="delivery_sla",
                    severity=severity,
                    source_type="delivery_task",
                    source_id=str(row.id),
                    title="طلب جاهز بدون مندوب",
                    message=(
                        f"مهمة التوصيل بدون مندوب منذ {age} دقيقة."
                    ),
                    details={
                        "task_id": str(row.id),
                        "order_id": str(row.order_id),
                        "chef_id": str(row.chef_id),
                        "age_minutes": age,
                    },
                )
            )

        # Promised delivery window warning / late breach.
        promise_warning_cutoff = now + timedelta(
            minutes=self.settings.ops_delivery_promise_warning_minutes
        )
        promised_orders = list(
            self.db.scalars(
                select(OrderEntity).where(
                    OrderEntity.status.in_(
                        [
                            "confirmed",
                            "accepted_by_chef",
                            "preparing",
                            "ready_for_pickup",
                            "assigned_to_driver",
                            "picked_up",
                            "out_for_delivery",
                        ]
                    ),
                    OrderEntity.promised_delivery_window_end_at.is_not(None),
                    OrderEntity.promised_delivery_window_end_at
                    <= promise_warning_cutoff,
                )
            ).all()
        )
        for order in promised_orders:
            deadline = _aware(order.promised_delivery_window_end_at)
            seconds = (deadline - _aware(now)).total_seconds()
            if seconds <= 0:
                overdue = max(1, int((-seconds + 59) // 60))
                severity = "critical"
                title = "الطلب تجاوز وعد التوصيل"
                message = (
                    f"الطلب متأخر عن نهاية نافذة التوصيل بحوالي "
                    f"{overdue} دقيقة."
                )
                timing = {
                    "overdue_minutes": overdue,
                    "remaining_minutes": 0,
                }
            else:
                remaining = max(1, int((seconds + 59) // 60))
                severity = "high"
                title = "موعد التوصيل يقترب"
                message = (
                    f"متبقي حوالي {remaining} دقيقة على نهاية "
                    "نافذة التوصيل والطلب لم يُسلّم بعد."
                )
                timing = {
                    "overdue_minutes": 0,
                    "remaining_minutes": remaining,
                }

            candidates.append(
                AlertCandidate(
                    fingerprint=f"delivery_promise:{order.id}",
                    category="delivery_sla",
                    severity=severity,
                    source_type="order",
                    source_id=str(order.id),
                    title=title,
                    message=message,
                    details={
                        "order_id": str(order.id),
                        "order_status": order.status,
                        "promised_delivery_window_start_at": (
                            _aware(
                                order.promised_delivery_window_start_at
                            ).isoformat()
                            if order.promised_delivery_window_start_at
                            else None
                        ),
                        "promised_delivery_window_end_at": deadline.isoformat(),
                        "promised_delivery_timezone": (
                            order.promised_delivery_timezone
                        ),
                        **timing,
                    },
                )
            )

        # Active delivery issues are always operationally visible.
        issue_rows = list(
            self.db.scalars(
                select(DeliveryTaskEntity).where(
                    DeliveryTaskEntity.status == "delivery_issue"
                )
            ).all()
        )
        for row in issue_rows:
            candidates.append(
                AlertCandidate(
                    fingerprint=f"delivery_issue:{row.id}",
                    category="delivery_sla",
                    severity="high",
                    source_type="delivery_task",
                    source_id=str(row.id),
                    title="مشكلة توصيل نشطة",
                    message=row.issue_note or "هناك مشكلة نشطة في مهمة التوصيل.",
                    details={
                        "task_id": str(row.id),
                        "order_id": str(row.order_id),
                        "driver_id": str(row.driver_id) if row.driver_id else None,
                        "issue_code": row.issue_code,
                    },
                )
            )

        # Support SLA.
        support_rows = list(
            self.db.scalars(
                select(SupportTicketEntity).where(
                    SupportTicketEntity.status.in_(OPEN_SUPPORT)
                )
            ).all()
        )
        for row in support_rows:
            sla = self._support_sla_minutes(row.priority)
            age = _minutes_between(row.created_at, now)
            if age < sla:
                continue
            severity = (
                "critical"
                if row.priority == "urgent"
                else "high"
                if row.priority == "high"
                else "warning"
            )
            candidates.append(
                AlertCandidate(
                    fingerprint=f"support_sla:{row.id}",
                    category="support_sla",
                    severity=severity,
                    source_type="support_ticket",
                    source_id=str(row.id),
                    title="تذكرة دعم تجاوزت SLA",
                    message=(
                        f"تذكرة {row.priority} مفتوحة منذ {age} دقيقة "
                        f"(SLA = {sla} دقيقة)."
                    ),
                    details={
                        "ticket_id": str(row.id),
                        "priority": row.priority,
                        "status": row.status,
                        "age_minutes": age,
                        "sla_minutes": sla,
                        "assigned_admin_id": (
                            str(row.assigned_admin_id)
                            if row.assigned_admin_id
                            else None
                        ),
                    },
                )
            )

        # Financial reconciliation.
        payment_issues = list(
            self.db.scalars(
                select(PaymentReconciliationIssueEntity).where(
                    PaymentReconciliationIssueEntity.status == "open"
                )
            ).all()
        )
        for row in payment_issues:
            candidates.append(
                AlertCandidate(
                    fingerprint=f"payment_reconciliation:{row.id}",
                    category="payment",
                    severity="critical",
                    source_type="payment_reconciliation",
                    source_id=str(row.id),
                    title="مشكلة تسوية مالية مفتوحة",
                    message=(
                        f"نوع المشكلة: {row.issue_type}. "
                        "تحتاج مراجعة قبل الاعتماد على الأرقام المالية."
                    ),
                    details={
                        "issue_id": str(row.id),
                        "issue_type": row.issue_type,
                        "payment_id": (
                            str(row.payment_id) if row.payment_id else None
                        ),
                        "provider_transaction_id": row.provider_transaction_id,
                    },
                )
            )

        blocked_settlements = list(
            self.db.scalars(
                select(ProviderSettlementBatchEntity).where(
                    ProviderSettlementBatchEntity.status == "blocked"
                )
            ).all()
        )
        for row in blocked_settlements:
            candidates.append(
                AlertCandidate(
                    fingerprint=f"provider_settlement_blocked:{row.id}",
                    category="payment",
                    severity="critical",
                    source_type="provider_settlement",
                    source_id=str(row.id),
                    title="تسوية مزود مالية محجوبة",
                    message=(
                        f"دفعة تسوية {row.provider} تحتوي اختلافات "
                        "وتمنع الاعتماد المالي/التوسع."
                    ),
                    details={
                        "settlement_batch_id": str(row.id),
                        "provider": row.provider,
                        "reference": row.external_reference,
                        "mismatched_lines": row.mismatched_lines,
                        "blockers": row.blockers_json,
                    },
                )
            )

        # Sprint 48 Expansion Zone traffic/capacity health.
        expansion_zones = list(
            self.db.scalars(
                select(ExpansionZoneEntity).where(
                    ExpansionZoneEntity.status.in_(["live", "paused"])
                )
            ).all()
        )
        for zone in expansion_zones:
            snapshot = self.db.scalar(
                select(ExpansionMonitoringSnapshotEntity)
                .where(
                    ExpansionMonitoringSnapshotEntity.zone_id == zone.id
                )
                .order_by(
                    ExpansionMonitoringSnapshotEntity.observed_at.desc()
                )
                .limit(1)
            )
            if snapshot is None or snapshot.health == "green":
                continue
            severity = "critical" if snapshot.health == "red" else "high"
            candidates.append(
                AlertCandidate(
                    fingerprint=f"expansion_traffic_health:{zone.id}",
                    category="traffic",
                    severity=severity,
                    source_type="expansion_zone",
                    source_id=str(zone.id),
                    title="ضغط تشغيل في منطقة التوسع",
                    message=(
                        f"{zone.area}: traffic health={snapshot.health}; "
                        f"daily={snapshot.daily_utilization_pct}%، "
                        f"hourly={snapshot.hourly_utilization_pct}%، "
                        f"rejections={snapshot.rejection_rate_pct}%."
                    ),
                    details={
                        "zone_id": str(zone.id),
                        "area": zone.area,
                        "rollout_stage": zone.rollout_stage,
                        "rollout_percent": zone.rollout_percent,
                        "daily_utilization_pct": snapshot.daily_utilization_pct,
                        "hourly_utilization_pct": snapshot.hourly_utilization_pct,
                        "rejection_rate_pct": snapshot.rejection_rate_pct,
                        "available_drivers": snapshot.available_drivers,
                        "open_chefs": snapshot.open_chefs,
                        "blockers": snapshot.blockers_json,
                        "snapshot_id": str(snapshot.id),
                    },
                )
            )

        # Dead-letter reliability items.
        for row in self.db.scalars(
            select(OutboxEventEntity).where(
                OutboxEventEntity.status == "dead_letter"
            )
        ).all():
            candidates.append(
                AlertCandidate(
                    fingerprint=f"outbox_dead:{row.id}",
                    category="reliability",
                    severity="critical",
                    source_type="outbox_event",
                    source_id=str(row.id),
                    title="Outbox Dead Letter",
                    message="حدث Outbox فشل نهائيًا ويحتاج تدخلًا.",
                    details={
                        "event_id": str(row.id),
                        "event_type": row.event_type,
                        "attempts": row.attempts,
                    },
                )
            )

        for row in self.db.scalars(
            select(BackgroundJobEntity).where(
                BackgroundJobEntity.status == "dead_letter"
            )
        ).all():
            candidates.append(
                AlertCandidate(
                    fingerprint=f"job_dead:{row.id}",
                    category="reliability",
                    severity="critical",
                    source_type="background_job",
                    source_id=str(row.id),
                    title="Background Job Dead Letter",
                    message="مهمة خلفية فشلت نهائيًا وتحتاج تدخلًا.",
                    details={
                        "job_id": str(row.id),
                        "job_type": row.job_type,
                        "attempts": row.attempts,
                    },
                )
            )

        # Stale worker heartbeat.
        worker_cutoff = now - timedelta(seconds=self.settings.worker_stale_seconds)
        workers = list(self.db.scalars(select(WorkerHeartbeatEntity)).all())
        for row in workers:
            if _aware(row.last_seen_at) >= worker_cutoff:
                continue
            stale_seconds = int(
                (_aware(now) - _aware(row.last_seen_at)).total_seconds()
            )
            candidates.append(
                AlertCandidate(
                    fingerprint=f"worker_stale:{row.worker_id}",
                    category="reliability",
                    severity="critical",
                    source_type="worker",
                    source_id=row.worker_id,
                    title="Worker heartbeat متأخر",
                    message=(
                        f"الـWorker لم يرسل heartbeat منذ "
                        f"{stale_seconds} ثانية."
                    ),
                    details={
                        "worker_id": row.worker_id,
                        "status": row.status,
                        "stale_seconds": stale_seconds,
                        "last_seen_at": _aware(row.last_seen_at).isoformat(),
                    },
                )
            )

        # Notification dead letters.
        notification_rows = list(
            self.db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.status == "dead_letter"
                )
            ).all()
        )
        for row in notification_rows:
            candidates.append(
                AlertCandidate(
                    fingerprint=f"notification_dead:{row.id}",
                    category="notifications",
                    severity="high",
                    source_type="notification_delivery",
                    source_id=str(row.id),
                    title="فشل نهائي في إرسال إشعار",
                    message=(
                        f"قناة {row.channel} / مزود {row.provider} "
                        "وصلت إلى dead-letter."
                    ),
                    details={
                        "delivery_id": str(row.id),
                        "channel": row.channel,
                        "provider": row.provider,
                        "provider_status": row.provider_status,
                        "provider_error_code": row.provider_error_code,
                    },
                )
            )

        return candidates

    def _notify_admins(
        self,
        *,
        incident: OperationsIncidentEntity,
        event: str,
    ) -> int:
        threshold = SEVERITY_RANK.get(
            self.settings.ops_notification_min_severity,
            SEVERITY_RANK["high"],
        )
        if SEVERITY_RANK.get(incident.severity, 9) > threshold:
            return 0

        admins = list(
            self.db.scalars(
                select(UserEntity).where(
                    UserEntity.role == "admin",
                    UserEntity.is_active.is_(True),
                )
            ).all()
        )
        count = 0
        for admin in admins:
            NotificationService(self.db, self.settings).emit(
                user_id=admin.id,
                kind="ops_incident",
                title=f"[{incident.severity.upper()}] {incident.title}",
                body=incident.message,
                dedupe_key=(
                    f"ops:{incident.id}:{event}:{incident.severity}"
                ),
                action_url="/control-room",
                data_json={
                    "incident_id": str(incident.id),
                    "severity": incident.severity,
                    "category": incident.category,
                    "source_type": incident.source_type,
                    "source_id": incident.source_id,
                    "event": event,
                },
            )
            count += 1
        return count

    @staticmethod
    def _merge_incident_details(
        existing_details: dict | None,
        detected_details: dict,
    ) -> dict:
        preserved = {}
        for key in (
            "manual_escalation",
            "auto_escalation",
        ):
            if existing_details and key in existing_details:
                preserved[key] = existing_details[key]
        return {**detected_details, **preserved}

    def refresh_incidents(self) -> IncidentRefreshResponse:
        now = utc_now()
        candidates = self.detect_candidates()
        active_fingerprints = {x.fingerprint for x in candidates}

        existing = {
            row.fingerprint: row
            for row in self.db.scalars(
                select(OperationsIncidentEntity)
            ).all()
        }

        created = 0
        updated = 0
        auto_resolved = 0
        auto_escalated = 0
        notification_events: list[
            tuple[OperationsIncidentEntity, str]
        ] = []

        for candidate in candidates:
            row = existing.get(candidate.fingerprint)
            if row is None:
                row = OperationsIncidentEntity(
                    fingerprint=candidate.fingerprint,
                    category=candidate.category,
                    severity=candidate.severity,
                    status="open",
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    title=candidate.title,
                    message=candidate.message,
                    details_json=candidate.details,
                    detected_at=now,
                    last_detected_at=now,
                )
                self.db.add(row)
                self.db.flush()
                existing[candidate.fingerprint] = row
                created += 1
                notification_events.append((row, "created"))
                continue

            previous_severity = row.severity
            reopened = row.status == "resolved"
            if reopened:
                row.status = "open"
                row.detected_at = now
                row.acknowledged_at = None
                row.acknowledged_by_admin_id = None
                row.resolved_at = None
                row.resolved_by_admin_id = None
                row.resolution_note = None

            row.category = candidate.category
            if reopened:
                row.severity = candidate.severity
            else:
                # Preserve a manual/automatic higher active severity.
                row.severity = min(
                    [row.severity, candidate.severity],
                    key=lambda value: SEVERITY_RANK.get(value, 9),
                )
            row.source_type = candidate.source_type
            row.source_id = candidate.source_id
            row.title = candidate.title
            row.message = candidate.message
            row.details_json = self._merge_incident_details(
                row.details_json,
                candidate.details,
            )
            row.last_detected_at = now
            updated += 1

            if reopened:
                notification_events.append((row, "reopened"))
            elif (
                SEVERITY_RANK.get(row.severity, 9)
                < SEVERITY_RANK.get(previous_severity, 9)
            ):
                notification_events.append((row, "severity_increased"))

        if self.settings.ops_incident_auto_resolve:
            for row in existing.values():
                if (
                    row.status in ACTIVE_INCIDENT
                    and row.fingerprint not in active_fingerprints
                ):
                    row.status = "resolved"
                    row.resolved_at = now
                    row.resolution_note = "auto_resolved_condition_cleared"
                    auto_resolved += 1

        # Unacknowledged incidents are automatically escalated if nobody
        # takes ownership within the configured escalation window.
        escalation_window = timedelta(
            minutes=self.settings.ops_incident_auto_escalate_minutes
        )
        for row in existing.values():
            if row.status != "open" or row.severity == "critical":
                continue

            details = dict(row.details_json or {})
            escalation = dict(details.get("auto_escalation") or {})
            last_raw = escalation.get("last_at")
            if last_raw:
                try:
                    reference = datetime.fromisoformat(last_raw)
                except ValueError:
                    reference = row.detected_at
            else:
                reference = row.detected_at

            if _aware(now) - _aware(reference) < escalation_window:
                continue

            previous = row.severity
            row.severity = {
                "info": "warning",
                "warning": "high",
                "high": "critical",
                "critical": "critical",
            }[row.severity]
            escalation["count"] = int(escalation.get("count") or 0) + 1
            escalation["from"] = previous
            escalation["to"] = row.severity
            escalation["last_at"] = now.isoformat()
            details["auto_escalation"] = escalation
            row.details_json = details
            auto_escalated += 1
            notification_events.append((row, "auto_escalated"))

        admin_notifications = 0
        for row, event in notification_events:
            admin_notifications += self._notify_admins(
                incident=row,
                event=event,
            )

        self.db.commit()

        active_count = int(
            self.db.scalar(
                select(func.count(OperationsIncidentEntity.id)).where(
                    OperationsIncidentEntity.status.in_(ACTIVE_INCIDENT)
                )
            )
            or 0
        )
        return IncidentRefreshResponse(
            detected=len(candidates),
            created=created,
            updated=updated,
            auto_resolved=auto_resolved,
            auto_escalated=auto_escalated,
            admin_notifications_planned=admin_notifications,
            active_incidents=active_count,
        )

    def list_incidents(
        self,
        *,
        status: str | None,
        severity: str | None,
        category: str | None,
        limit: int,
    ) -> list[IncidentResponse]:
        stmt = select(OperationsIncidentEntity)
        if status:
            stmt = stmt.where(OperationsIncidentEntity.status == status)
        if severity:
            stmt = stmt.where(OperationsIncidentEntity.severity == severity)
        if category:
            stmt = stmt.where(OperationsIncidentEntity.category == category)

        rows = list(
            self.db.scalars(
                stmt.order_by(
                    OperationsIncidentEntity.last_detected_at.desc()
                ).limit(limit)
            ).all()
        )
        rows.sort(
            key=lambda row: (
                1 if row.status == "resolved" else 0,
                SEVERITY_RANK.get(row.severity, 9),
                -_aware(row.last_detected_at).timestamp(),
            )
        )
        return [IncidentResponse.model_validate(row) for row in rows]

    def acknowledge(
        self,
        *,
        incident_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> IncidentResponse:
        row = self._incident(incident_id)
        if row.status == "resolved":
            raise ApiError(
                409,
                "incident_already_resolved",
                "الحادثة تم حلها بالفعل.",
            )
        row.status = "acknowledged"
        row.acknowledged_at = utc_now()
        row.acknowledged_by_admin_id = admin_id
        if row.owner_admin_id is None:
            row.owner_admin_id = admin_id
        self.audit.add(
            action="operations.incident.acknowledge",
            actor_user_id=admin_id,
            entity_type="operations_incident",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"severity": row.severity, "category": row.category},
        )
        self.db.commit()
        self.db.refresh(row)
        return IncidentResponse.model_validate(row)

    def assign(
        self,
        *,
        incident_id: UUID,
        owner_admin_id: UUID | None,
        actor_admin_id: UUID,
        request_id: str | None,
    ) -> IncidentResponse:
        row = self._incident(incident_id)
        if row.status == "resolved":
            raise ApiError(
                409,
                "incident_already_resolved",
                "لا يمكن تعيين حادثة محلولة.",
            )
        row.owner_admin_id = owner_admin_id
        self.audit.add(
            action="operations.incident.assign",
            actor_user_id=actor_admin_id,
            entity_type="operations_incident",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "owner_admin_id": (
                    str(owner_admin_id) if owner_admin_id else None
                )
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return IncidentResponse.model_validate(row)

    def escalate(
        self,
        *,
        incident_id: UUID,
        admin_id: UUID,
        note: str | None,
        request_id: str | None,
    ) -> IncidentResponse:
        row = self._incident(incident_id)
        if row.status == "resolved":
            raise ApiError(
                409,
                "incident_already_resolved",
                "لا يمكن تصعيد حادثة محلولة.",
            )

        next_severity = {
            "info": "warning",
            "warning": "high",
            "high": "critical",
            "critical": "critical",
        }[row.severity]
        previous = row.severity
        row.severity = next_severity
        if row.owner_admin_id is None:
            row.owner_admin_id = admin_id
        details = dict(row.details_json or {})
        details["manual_escalation"] = {
            "from": previous,
            "to": next_severity,
            "note": note,
            "at": utc_now().isoformat(),
            "by_admin_id": str(admin_id),
        }
        row.details_json = details

        self.audit.add(
            action="operations.incident.escalate",
            actor_user_id=admin_id,
            entity_type="operations_incident",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "from": previous,
                "to": next_severity,
                "note": note,
            },
        )
        if next_severity != previous:
            self._notify_admins(
                incident=row,
                event="manual_escalated",
            )
        self.db.commit()
        self.db.refresh(row)
        return IncidentResponse.model_validate(row)

    def resolve(
        self,
        *,
        incident_id: UUID,
        admin_id: UUID,
        note: str,
        request_id: str | None,
    ) -> IncidentResponse:
        row = self._incident(incident_id)
        if row.status == "resolved":
            return IncidentResponse.model_validate(row)
        row.status = "resolved"
        row.resolved_at = utc_now()
        row.resolved_by_admin_id = admin_id
        row.resolution_note = note
        self.audit.add(
            action="operations.incident.resolve",
            actor_user_id=admin_id,
            entity_type="operations_incident",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"note": note[:500]},
        )
        self.db.commit()
        self.db.refresh(row)
        return IncidentResponse.model_validate(row)

    def _incident(self, incident_id: UUID) -> OperationsIncidentEntity:
        row = self.db.get(OperationsIncidentEntity, incident_id)
        if row is None:
            raise ApiError(
                404,
                "operations_incident_not_found",
                "الحادثة التشغيلية غير موجودة.",
            )
        return row

    def launch_kpis(self, days: int = 7) -> LaunchKpis:
        if days < 1 or days > 90:
            raise ApiError(
                422,
                "control_room_days_invalid",
                "عدد الأيام يجب أن يكون بين 1 و90.",
            )

        now = utc_now()
        start = now - timedelta(days=days)
        orders = list(
            self.db.scalars(
                select(OrderEntity).where(OrderEntity.created_at >= start)
            ).all()
        )
        delivered = [x for x in orders if x.status == "delivered"]
        cancelled = [
            x for x in orders if x.status in {"cancelled", "expired"}
        ]
        completed_count = len(delivered) + len(cancelled)

        reviews = list(
            self.db.scalars(
                select(ReviewEntity).where(ReviewEntity.created_at >= start)
            ).all()
        )
        average_rating = (
            round(sum(x.chef_overall for x in reviews) / len(reviews), 2)
            if reviews
            else 0.0
        )

        retention = AnalyticsService(self.db).retention(min(days, 90))

        fulfillments = list(
            self.db.scalars(
                select(ChefOrderFulfillmentEntity).where(
                    ChefOrderFulfillmentEntity.created_at >= start,
                    ChefOrderFulfillmentEntity.acceptance_deadline_at.is_not(None),
                )
            ).all()
        )
        chef_breaches = 0
        for row in fulfillments:
            deadline = _aware(row.acceptance_deadline_at)
            if row.accepted_at is not None:
                if _aware(row.accepted_at) > deadline:
                    chef_breaches += 1
            elif row.stage == "new" and _aware(now) > deadline:
                chef_breaches += 1

        support_rows = list(
            self.db.scalars(
                select(SupportTicketEntity).where(
                    SupportTicketEntity.created_at >= start
                )
            ).all()
        )
        support_breaches = 0
        for row in support_rows:
            end = (
                row.resolved_at
                or row.closed_at
                or now
            )
            elapsed = _minutes_between(row.created_at, end)
            if elapsed >= self._support_sla_minutes(row.priority):
                support_breaches += 1

        payment_open = int(
            self.db.scalar(
                select(func.count(PaymentReconciliationIssueEntity.id)).where(
                    PaymentReconciliationIssueEntity.status == "open"
                )
            )
            or 0
        )
        notification_dead = int(
            self.db.scalar(
                select(func.count(NotificationDeliveryEntity.id)).where(
                    NotificationDeliveryEntity.status == "dead_letter"
                )
            )
            or 0
        )
        outbox_dead = int(
            self.db.scalar(
                select(func.count(OutboxEventEntity.id)).where(
                    OutboxEventEntity.status == "dead_letter"
                )
            )
            or 0
        )
        jobs_dead = int(
            self.db.scalar(
                select(func.count(BackgroundJobEntity.id)).where(
                    BackgroundJobEntity.status == "dead_letter"
                )
            )
            or 0
        )

        worker_cutoff = now - timedelta(
            seconds=self.settings.worker_stale_seconds
        )
        stale_workers = 0
        for row in self.db.scalars(select(WorkerHeartbeatEntity)).all():
            if _aware(row.last_seen_at) < worker_cutoff:
                stale_workers += 1

        delivery_success = (
            round(len(delivered) / completed_count * 100, 2)
            if completed_count
            else 0.0
        )
        cancellation_rate = (
            round(len(cancelled) / len(orders) * 100, 2)
            if orders
            else 0.0
        )

        # Launch targets are only considered met when sample data exists.
        rating_met = bool(reviews) and average_rating >= 4.7
        repeat_met = (
            retention.unique_customers > 0
            and retention.repeat_customer_rate_pct >= 40.0
        )
        delivered_tasks = {
            task.order_id: task
            for task in self.db.scalars(
                select(DeliveryTaskEntity).where(
                    DeliveryTaskEntity.order_id.in_(
                        [x.id for x in delivered]
                    )
                )
            ).all()
        } if delivered else {}

        measurable_deliveries = []
        on_time_deliveries = 0
        late_deliveries = 0
        for order in delivered:
            task = delivered_tasks.get(order.id)
            if (
                order.promised_delivery_window_end_at is None
                or task is None
                or task.delivered_at is None
            ):
                continue
            measurable_deliveries.append(order.id)
            if (
                _aware(task.delivered_at)
                <= _aware(order.promised_delivery_window_end_at)
            ):
                on_time_deliveries += 1
            else:
                late_deliveries += 1

        measurable_count = len(measurable_deliveries)
        promise_coverage = (
            round(measurable_count / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )
        on_time_rate = (
            round(on_time_deliveries / measurable_count * 100, 2)
            if measurable_count
            else None
        )
        # The launch gate is only valid when every delivered order in the
        # measurement sample has an immutable promise snapshot.
        on_time_met = (
            on_time_rate >= 95.0
            if on_time_rate is not None
            and promise_coverage == 100.0
            else None
        )
        cancellation_met = bool(orders) and cancellation_rate < 5.0

        return LaunchKpis(
            days=days,
            orders_created=len(orders),
            delivered_orders=len(delivered),
            cancelled_orders=len(cancelled),
            cancellation_rate_pct=cancellation_rate,
            delivery_success_rate_pct=delivery_success,
            gmv_minor=sum(x.total_minor for x in delivered),
            repeat_customer_rate_pct=retention.repeat_customer_rate_pct,
            average_chef_rating=average_rating,
            reviews_count=len(reviews),
            chef_acceptance_sla_breaches=chef_breaches,
            support_sla_breaches=support_breaches,
            payment_reconciliation_open=payment_open,
            notification_dead_letters=notification_dead,
            outbox_dead_letters=outbox_dead,
            background_job_dead_letters=jobs_dead,
            stale_workers=stale_workers,
            launch_target_rating_met=rating_met,
            launch_target_repeat_met=repeat_met,
            on_time_delivery_rate_pct=on_time_rate,
            on_time_measurable_deliveries=measurable_count,
            late_deliveries=late_deliveries,
            delivery_promise_coverage_pct=promise_coverage,
            launch_target_on_time_met=on_time_met,
            launch_target_cancellation_met=cancellation_met,
        )

    def overview(self) -> ControlRoomOverview:
        active = list(
            self.db.scalars(
                select(OperationsIncidentEntity).where(
                    OperationsIncidentEntity.status.in_(ACTIVE_INCIDENT)
                )
            ).all()
        )
        active.sort(
            key=lambda row: (
                SEVERITY_RANK.get(row.severity, 9),
                -_aware(row.last_detected_at).timestamp(),
            )
        )

        critical = sum(x.severity == "critical" for x in active)
        high = sum(x.severity == "high" for x in active)
        unack = sum(x.status == "open" for x in active)

        if critical:
            health = "red"
        elif high or active:
            health = "amber"
        else:
            health = "green"

        urgent_support = int(
            self.db.scalar(
                select(func.count(SupportTicketEntity.id)).where(
                    SupportTicketEntity.status.in_(OPEN_SUPPORT),
                    SupportTicketEntity.priority == "urgent",
                )
            )
            or 0
        )
        payment_open = int(
            self.db.scalar(
                select(func.count(PaymentReconciliationIssueEntity.id)).where(
                    PaymentReconciliationIssueEntity.status == "open"
                )
            )
            or 0
        )

        workers = list(
            self.db.scalars(
                select(WorkerHeartbeatEntity).order_by(
                    WorkerHeartbeatEntity.last_seen_at.desc()
                )
            ).all()
        )
        if not workers:
            worker_status = "no_workers"
        else:
            cutoff = utc_now() - timedelta(
                seconds=self.settings.worker_stale_seconds
            )
            worker_status = (
                "stale"
                if any(_aware(x.last_seen_at) < cutoff for x in workers)
                else "healthy"
            )

        return ControlRoomOverview(
            generated_at=utc_now(),
            health=health,
            active_incidents=len(active),
            critical_incidents=critical,
            high_incidents=high,
            unacknowledged_incidents=unack,
            urgent_support_open=urgent_support,
            open_payment_reconciliation=payment_open,
            worker_status=worker_status,
            kpis=self.launch_kpis(7),
            top_incidents=[
                IncidentResponse.model_validate(x) for x in active[:8]
            ],
        )

    def daily_brief(self, day: date | None = None) -> DailyBrief:
        target = day or utc_now().date()
        start = datetime.combine(
            target,
            time.min,
            tzinfo=timezone.utc,
        )
        end = start + timedelta(days=1)

        orders = list(
            self.db.scalars(
                select(OrderEntity).where(
                    OrderEntity.created_at >= start,
                    OrderEntity.created_at < end,
                )
            ).all()
        )
        active = list(
            self.db.scalars(
                select(OperationsIncidentEntity).where(
                    OperationsIncidentEntity.status.in_(ACTIVE_INCIDENT)
                )
            ).all()
        )
        active.sort(
            key=lambda row: SEVERITY_RANK.get(row.severity, 9)
        )
        critical = sum(x.severity == "critical" for x in active)
        urgent_support = int(
            self.db.scalar(
                select(func.count(SupportTicketEntity.id)).where(
                    SupportTicketEntity.status.in_(OPEN_SUPPORT),
                    SupportTicketEntity.priority == "urgent",
                )
            )
            or 0
        )
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
                select(func.count(ChefProfileEntity.user_id)).where(
                    ChefProfileEntity.status == "active",
                    ChefProfileEntity.is_open_today.is_(True),
                )
            )
            or 0
        )

        if critical:
            health = "red"
        elif active:
            health = "amber"
        else:
            health = "green"

        actions: list[DailyActionItem] = []
        for row in active[:5]:
            route = None
            if row.source_type == "order" and row.source_id:
                route = f"/orders/{row.source_id}"
            elif row.source_type == "support_ticket" and row.source_id:
                route = f"/support/{row.source_id}"
            elif row.category == "payment":
                route = "/finance"
            actions.append(
                DailyActionItem(
                    priority=row.severity,
                    title=row.title,
                    detail=row.message,
                    route=route,
                )
            )

        if available_drivers == 0:
            actions.append(
                DailyActionItem(
                    priority="high",
                    title="لا يوجد مندوب متاح",
                    detail="راجع تغطية المندوبين قبل زيادة الطلبات.",
                    route="/drivers",
                )
            )
        if open_chefs == 0:
            actions.append(
                DailyActionItem(
                    priority="warning",
                    title="لا يوجد مطبخ مفتوح",
                    detail="تأكد من فتح مطابخ الشيفات المخطط لها اليوم.",
                    route="/chefs",
                )
            )

        return DailyBrief(
            day=target,
            generated_at=utc_now(),
            health=health,
            opening_orders=len(orders),
            delivered_orders=sum(x.status == "delivered" for x in orders),
            cancelled_orders=sum(
                x.status in {"cancelled", "expired"} for x in orders
            ),
            gmv_minor=sum(
                x.total_minor for x in orders if x.status == "delivered"
            ),
            active_incidents=len(active),
            critical_incidents=critical,
            urgent_support_open=urgent_support,
            available_drivers=available_drivers,
            open_chefs=open_chefs,
            actions=actions[:8],
        )
