from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from math import ceil
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    DeliveryTaskEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    OperationsIncidentEntity,
    PaymentEntity,
    PaymentReconciliationIssueEntity,
    PilotProgramEntity,
    PilotQaEvidenceEntity,
    PilotWeeklySnapshotEntity,
    RefundEntity,
    ReviewEntity,
    SupportTicketEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.pilot_stability.schemas import (
    CohortRetentionCell,
    PilotCohortReport,
    PilotCohortRow,
    PilotPostPilotReport,
    PilotProgramCreate,
    PilotProgramResponse,
    PilotQaEvidenceResponse,
    PilotQaEvidenceUpsert,
    PilotStabilityReport,
    PilotWeeklySnapshotResponse,
)

MANDATORY_SCALE_EVIDENCE = (
    "pilot_qa_exit",
    "operations_signoff",
)


def _bounds(start_day: date, end_day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_day, time.min, tzinfo=timezone.utc),
        datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def _aware(value: datetime) -> datetime:
    return ensure_utc(value)


class PilotStabilityService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    # ----------------------------------------------------------
    # Program lifecycle
    # ----------------------------------------------------------
    def create_program(
        self,
        *,
        payload: PilotProgramCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> PilotProgramResponse:
        row = PilotProgramEntity(
            name=payload.name.strip(),
            area=(payload.area or "").strip() or None,
            start_date=payload.start_date,
            end_date=payload.end_date,
            required_stability_weeks=payload.required_stability_weeks,
            rating_target=payload.rating_target,
            repeat_customer_target_pct=payload.repeat_customer_target_pct,
            on_time_target_pct=payload.on_time_target_pct,
            cancellation_max_pct=payload.cancellation_max_pct,
            notes=payload.notes,
            created_by_admin_id=admin_id,
            status="planned",
        )
        self.db.add(row)
        self.db.flush()
        self.audit.add(
            action="pilot.program.created",
            actor_user_id=admin_id,
            entity_type="pilot_program",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "start_date": str(row.start_date),
                "end_date": str(row.end_date) if row.end_date else None,
                "area": row.area,
                "required_stability_weeks": row.required_stability_weeks,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return PilotProgramResponse.model_validate(row)

    def programs(self) -> list[PilotProgramResponse]:
        rows = list(
            self.db.scalars(
                select(PilotProgramEntity).order_by(
                    PilotProgramEntity.created_at.desc()
                )
            ).all()
        )
        return [PilotProgramResponse.model_validate(x) for x in rows]

    def program(self, program_id: UUID) -> PilotProgramEntity:
        row = self.db.get(PilotProgramEntity, program_id)
        if row is None:
            raise ApiError(
                404,
                "pilot_program_not_found",
                "برنامج الطيار غير موجود.",
            )
        return row

    def activate(
        self,
        *,
        program_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> PilotProgramResponse:
        row = self.program(program_id)
        if row.status == "active":
            return PilotProgramResponse.model_validate(row)
        if row.status in {"completed", "archived"}:
            raise ApiError(
                409,
                "pilot_program_not_activatable",
                "لا يمكن تفعيل برنامج مكتمل أو مؤرشف.",
            )
        other = self.db.scalar(
            select(PilotProgramEntity).where(
                PilotProgramEntity.status == "active",
                PilotProgramEntity.id != row.id,
            )
        )
        if other is not None:
            raise ApiError(
                409,
                "pilot_program_active_exists",
                "يوجد برنامج طيار نشط بالفعل.",
            )
        row.status = "active"
        row.activated_at = utc_now()
        self.audit.add(
            action="pilot.program.activated",
            actor_user_id=admin_id,
            entity_type="pilot_program",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.refresh_program(row.id)
        self.db.refresh(row)
        return PilotProgramResponse.model_validate(row)

    def complete(
        self,
        *,
        program_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> PilotProgramResponse:
        row = self.program(program_id)
        if row.status == "completed":
            return PilotProgramResponse.model_validate(row)
        if row.status == "archived":
            raise ApiError(
                409,
                "pilot_program_archived",
                "البرنامج مؤرشف.",
            )
        today = utc_now().date()
        if row.end_date is None or row.end_date > today:
            row.end_date = today
        row.status = "completed"
        row.completed_at = utc_now()
        self.audit.add(
            action="pilot.program.completed",
            actor_user_id=admin_id,
            entity_type="pilot_program",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"end_date": str(row.end_date)},
        )
        self.db.commit()
        self.refresh_program(row.id)
        self.db.refresh(row)
        return PilotProgramResponse.model_validate(row)

    # ----------------------------------------------------------
    # Program-scoped data
    # ----------------------------------------------------------
    def _order_stmt(
        self,
        program: PilotProgramEntity,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ):
        stmt = select(OrderEntity)
        if program.area:
            stmt = stmt.join(
                OrderDeliveryAddressEntity,
                OrderDeliveryAddressEntity.order_id == OrderEntity.id,
            ).where(OrderDeliveryAddressEntity.area == program.area)
        if start_dt is not None:
            stmt = stmt.where(OrderEntity.created_at >= start_dt)
        if end_dt is not None:
            stmt = stmt.where(OrderEntity.created_at < end_dt)
        return stmt

    def _orders(
        self,
        program: PilotProgramEntity,
        start_day: date,
        end_day: date,
    ) -> list[OrderEntity]:
        start_dt, end_dt = _bounds(start_day, end_day)
        return list(
            self.db.scalars(
                self._order_stmt(program, start_dt, end_dt)
            ).all()
        )

    def _prior_delivered_customers(
        self,
        program: PilotProgramEntity,
        customer_ids: set[UUID],
        before: datetime,
    ) -> set[UUID]:
        if not customer_ids:
            return set()
        stmt = self._order_stmt(program, None, before).where(
            OrderEntity.status == "delivered",
            OrderEntity.customer_id.in_(customer_ids),
        )
        return set(self.db.scalars(stmt.with_only_columns(OrderEntity.customer_id)).all())

    def _week_values(
        self,
        *,
        program: PilotProgramEntity,
        week_index: int,
        week_start: date,
        week_end: date,
    ) -> dict:
        now_day = utc_now().date()
        orders = self._orders(program, week_start, week_end)
        order_ids = {x.id for x in orders}
        delivered = [x for x in orders if x.status == "delivered"]
        cancelled = [x for x in orders if x.status in {"cancelled", "expired"}]
        delivered_ids = {x.id for x in delivered}
        delivered_customers = {x.customer_id for x in delivered}

        start_dt, _ = _bounds(week_start, week_end)
        prior_customers = self._prior_delivered_customers(
            program,
            delivered_customers,
            start_dt,
        )
        repeat_customers = len(delivered_customers & prior_customers)
        repeat_rate = (
            round(repeat_customers / len(delivered_customers) * 100, 2)
            if delivered_customers
            else 0.0
        )

        reviews = []
        if order_ids:
            reviews = list(
                self.db.scalars(
                    select(ReviewEntity).where(
                        ReviewEntity.order_id.in_(order_ids)
                    )
                ).all()
            )
        average_rating = (
            round(sum(x.chef_overall for x in reviews) / len(reviews), 2)
            if reviews
            else None
        )

        tasks: dict[UUID, DeliveryTaskEntity] = {}
        if delivered_ids:
            tasks = {
                x.order_id: x
                for x in self.db.scalars(
                    select(DeliveryTaskEntity).where(
                        DeliveryTaskEntity.order_id.in_(delivered_ids)
                    )
                ).all()
            }
        measurable = 0
        on_time = 0
        late = 0
        for order in delivered:
            task = tasks.get(order.id)
            if (
                task is None
                or task.delivered_at is None
                or order.promised_delivery_window_end_at is None
            ):
                continue
            measurable += 1
            if _aware(task.delivered_at) <= _aware(
                order.promised_delivery_window_end_at
            ):
                on_time += 1
            else:
                late += 1

        coverage = (
            round(measurable / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )
        on_time_rate = (
            round(on_time / measurable * 100, 2)
            if measurable
            else None
        )

        payments = []
        refunds = []
        tickets = []
        if order_ids:
            payments = list(
                self.db.scalars(
                    select(PaymentEntity).where(
                        PaymentEntity.order_id.in_(order_ids),
                        PaymentEntity.status == "succeeded",
                    )
                ).all()
            )
            refunds = list(
                self.db.scalars(
                    select(RefundEntity).where(
                        RefundEntity.order_id.in_(order_ids),
                        RefundEntity.status == "succeeded",
                    )
                ).all()
            )
            tickets = list(
                self.db.scalars(
                    select(SupportTicketEntity).where(
                        SupportTicketEntity.order_id.in_(order_ids)
                    )
                ).all()
            )

        captured = sum(x.amount_minor for x in payments)
        refunded = sum(x.amount_minor for x in refunds)
        refunded_order_count = len({x.order_id for x in refunds})
        refund_rate = (
            round(refunded_order_count / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )
        cancellation_rate = (
            round(len(cancelled) / len(orders) * 100, 2)
            if orders
            else 0.0
        )

        is_full_week = (week_end - week_start).days == 6
        is_complete = now_day > week_end or (
            program.status == "completed"
            and program.end_date is not None
            and program.end_date >= week_end
        )

        rating_met = (
            average_rating >= program.rating_target
            if average_rating is not None
            else None
        )
        repeat_met = (
            repeat_rate >= program.repeat_customer_target_pct
            if delivered_customers
            else None
        )
        on_time_met = (
            on_time_rate >= program.on_time_target_pct
            if on_time_rate is not None and coverage == 100.0
            else None
        )
        cancellation_met = (
            cancellation_rate < program.cancellation_max_pct
            if orders
            else None
        )

        evaluable = bool(
            is_full_week
            and is_complete
            and orders
            and delivered
            and reviews
            and delivered_customers
            and coverage == 100.0
            and on_time_rate is not None
        )
        week_passed = (
            bool(
                rating_met
                and repeat_met
                and on_time_met
                and cancellation_met
            )
            if evaluable
            else None
        )

        return {
            "program_id": program.id,
            "week_index": week_index,
            "week_start": week_start,
            "week_end": week_end,
            "is_full_week": is_full_week,
            "is_complete": is_complete,
            "orders_created": len(orders),
            "delivered_orders": len(delivered),
            "cancelled_orders": len(cancelled),
            "cancellation_rate_pct": cancellation_rate,
            "unique_customers": len(delivered_customers),
            "repeat_customers": repeat_customers,
            "repeat_customer_rate_pct": repeat_rate,
            "average_chef_rating": average_rating,
            "reviews_count": len(reviews),
            "on_time_delivery_rate_pct": on_time_rate,
            "on_time_measurable_deliveries": measurable,
            "late_deliveries": late,
            "delivery_promise_coverage_pct": coverage,
            "gmv_minor": sum(x.total_minor for x in delivered),
            "captured_minor": captured,
            "refunded_minor": refunded,
            "net_collected_minor": max(0, captured - refunded),
            "support_tickets": len(tickets),
            "refund_count": len(refunds),
            "refund_rate_pct": refund_rate,
            "rating_met": rating_met,
            "repeat_met": repeat_met,
            "on_time_met": on_time_met,
            "cancellation_met": cancellation_met,
            "week_evaluable": evaluable,
            "week_passed": week_passed,
            "generated_at": utc_now(),
        }

    # ----------------------------------------------------------
    # Weekly snapshots / stability gate
    # ----------------------------------------------------------
    def refresh_program(
        self,
        program_id: UUID,
    ) -> list[PilotWeeklySnapshotResponse]:
        program = self.program(program_id)
        today = utc_now().date()
        if today < program.start_date:
            return []

        last_day = min(today, program.end_date) if program.end_date else today
        day_count = (last_day - program.start_date).days + 1
        weeks_to_include = max(1, ceil(day_count / 7))

        existing = {
            x.week_index: x
            for x in self.db.scalars(
                select(PilotWeeklySnapshotEntity).where(
                    PilotWeeklySnapshotEntity.program_id == program.id
                )
            ).all()
        }

        for index in range(1, weeks_to_include + 1):
            week_start = program.start_date + timedelta(days=(index - 1) * 7)
            planned_end = week_start + timedelta(days=6)
            week_end = (
                min(planned_end, program.end_date)
                if program.end_date is not None
                else planned_end
            )
            if week_start > last_day:
                break
            values = self._week_values(
                program=program,
                week_index=index,
                week_start=week_start,
                week_end=week_end,
            )
            row = existing.get(index)
            if row is None:
                row = PilotWeeklySnapshotEntity(**values)
                self.db.add(row)
                existing[index] = row
            else:
                for key, value in values.items():
                    if key in {"program_id", "week_index"}:
                        continue
                    setattr(row, key, value)

        self.db.commit()
        rows = list(
            self.db.scalars(
                select(PilotWeeklySnapshotEntity)
                .where(PilotWeeklySnapshotEntity.program_id == program.id)
                .order_by(PilotWeeklySnapshotEntity.week_index.asc())
            ).all()
        )
        return [PilotWeeklySnapshotResponse.model_validate(x) for x in rows]

    def refresh_active_programs(self) -> dict[str, int]:
        programs = list(
            self.db.scalars(
                select(PilotProgramEntity).where(
                    PilotProgramEntity.status == "active"
                )
            ).all()
        )
        snapshots = 0
        for program in programs:
            snapshots += len(self.refresh_program(program.id))
        return {
            "refreshed_programs": len(programs),
            "weekly_snapshots_seen": snapshots,
        }

    def stability_report(self, program_id: UUID) -> PilotStabilityReport:
        program = self.program(program_id)
        weeks = self.refresh_program(program_id)
        eligible = [
            x
            for x in weeks
            if x.is_full_week and x.is_complete
        ]

        current = 0
        for week in reversed(eligible):
            if week.week_passed is True:
                current += 1
            else:
                break

        maximum = 0
        streak = 0
        for week in eligible:
            if week.week_passed is True:
                streak += 1
                maximum = max(maximum, streak)
            else:
                streak = 0

        required = program.required_stability_weeks
        blockers: list[str] = []
        if len(eligible) < required:
            blockers.append(
                f"need_{required}_complete_full_weeks"
            )
        if current < required:
            blockers.append(
                f"current_consecutive_passed_weeks_{current}_of_{required}"
            )
        if any(x.is_complete and x.is_full_week and not x.week_evaluable for x in weeks):
            blockers.append("one_or_more_weeks_not_evaluable")

        return PilotStabilityReport(
            program=PilotProgramResponse.model_validate(program),
            required_weeks=required,
            complete_full_weeks=len(eligible),
            evaluable_weeks=sum(x.week_evaluable for x in eligible),
            passed_weeks=sum(x.week_passed is True for x in eligible),
            current_consecutive_passed_weeks=current,
            max_consecutive_passed_weeks=maximum,
            stability_gate_met=current >= required,
            blockers=blockers,
            weeks=weeks,
        )

    # ----------------------------------------------------------
    # Cohort retention
    # ----------------------------------------------------------
    def cohort_report(
        self,
        program_id: UUID,
        *,
        max_weeks: int,
    ) -> PilotCohortReport:
        if max_weeks < 1 or max_weeks > 26:
            raise ApiError(
                422,
                "pilot_cohort_weeks_invalid",
                "عدد أسابيع الكوهورت يجب أن يكون بين 1 و26.",
            )
        program = self.program(program_id)
        today = utc_now().date()
        end_day = min(today, program.end_date) if program.end_date else today
        if end_day < program.start_date:
            return PilotCohortReport(
                program_id=program.id,
                max_weeks=max_weeks,
                acquired_customers=0,
                cohorts=[],
            )

        _, range_end = _bounds(program.start_date, end_day)
        stmt = self._order_stmt(program, None, range_end).where(
            OrderEntity.status == "delivered"
        )
        all_delivered = list(
            self.db.scalars(
                stmt.order_by(OrderEntity.created_at.asc())
            ).all()
        )

        by_customer: dict[UUID, list[OrderEntity]] = defaultdict(list)
        for order in all_delivered:
            by_customer[order.customer_id].append(order)

        cohorts: dict[int, set[UUID]] = defaultdict(set)
        for customer_id, orders in by_customer.items():
            first = min(orders, key=lambda x: _aware(x.created_at))
            first_day = _aware(first.created_at).date()
            if not (program.start_date <= first_day <= end_day):
                continue
            cohort_week = (first_day - program.start_date).days // 7 + 1
            cohorts[cohort_week].add(customer_id)

        rows: list[PilotCohortRow] = []
        for cohort_week in sorted(cohorts):
            customers = cohorts[cohort_week]
            cohort_start = program.start_date + timedelta(
                days=(cohort_week - 1) * 7
            )
            cohort_end = min(
                cohort_start + timedelta(days=6),
                program.end_date or cohort_start + timedelta(days=6),
            )
            cells: list[CohortRetentionCell] = []
            for offset in range(max_weeks):
                cell_start = cohort_start + timedelta(days=offset * 7)
                if cell_start > end_day:
                    break
                cell_end = min(
                    cell_start + timedelta(days=6),
                    end_day,
                )
                active: set[UUID] = set()
                for customer_id in customers:
                    for order in by_customer[customer_id]:
                        order_day = _aware(order.created_at).date()
                        if cell_start <= order_day <= cell_end:
                            active.add(customer_id)
                            break
                cells.append(
                    CohortRetentionCell(
                        week_offset=offset,
                        active_customers=len(active),
                        retention_pct=(
                            round(len(active) / len(customers) * 100, 2)
                            if customers
                            else 0.0
                        ),
                    )
                )
            rows.append(
                PilotCohortRow(
                    cohort_week=cohort_week,
                    cohort_start=cohort_start,
                    cohort_end=cohort_end,
                    cohort_size=len(customers),
                    retention=cells,
                )
            )

        return PilotCohortReport(
            program_id=program.id,
            max_weeks=max_weeks,
            acquired_customers=sum(len(x) for x in cohorts.values()),
            cohorts=rows,
        )

    # ----------------------------------------------------------
    # QA evidence / scale decision
    # ----------------------------------------------------------
    def evidence(self, program_id: UUID) -> list[PilotQaEvidenceResponse]:
        self.program(program_id)
        rows = list(
            self.db.scalars(
                select(PilotQaEvidenceEntity)
                .where(PilotQaEvidenceEntity.program_id == program_id)
                .order_by(PilotQaEvidenceEntity.evidence_type.asc())
            ).all()
        )
        return [PilotQaEvidenceResponse.model_validate(x) for x in rows]

    def upsert_evidence(
        self,
        *,
        program_id: UUID,
        evidence_type: str,
        payload: PilotQaEvidenceUpsert,
        admin_id: UUID,
        request_id: str | None,
    ) -> PilotQaEvidenceResponse:
        self.program(program_id)
        normalized = evidence_type.strip().lower()
        if not normalized or len(normalized) > 80:
            raise ApiError(
                422,
                "pilot_evidence_type_invalid",
                "نوع الدليل غير صالح.",
            )
        row = self.db.scalar(
            select(PilotQaEvidenceEntity).where(
                PilotQaEvidenceEntity.program_id == program_id,
                PilotQaEvidenceEntity.evidence_type == normalized,
            )
        )
        if row is None:
            row = PilotQaEvidenceEntity(
                program_id=program_id,
                evidence_type=normalized,
            )
            self.db.add(row)
        row.status = payload.status
        row.reference = (payload.reference or "").strip() or None
        row.notes = payload.notes
        row.observed_at = payload.observed_at or (
            utc_now() if payload.status in {"passed", "failed"} else None
        )
        row.verified_by_admin_id = admin_id
        self.db.flush()
        self.audit.add(
            action="pilot.evidence.updated",
            actor_user_id=admin_id,
            entity_type="pilot_qa_evidence",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "program_id": str(program_id),
                "evidence_type": normalized,
                "status": row.status,
                "reference": row.reference,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return PilotQaEvidenceResponse.model_validate(row)

    # ----------------------------------------------------------
    # Post-pilot analytics / scale readiness
    # ----------------------------------------------------------
    def post_pilot_report(self, program_id: UUID) -> PilotPostPilotReport:
        program = self.program(program_id)
        today = utc_now().date()
        end_day = min(today, program.end_date) if program.end_date else today
        if end_day < program.start_date:
            end_day = program.start_date
        orders = self._orders(program, program.start_date, end_day)
        delivered = [x for x in orders if x.status == "delivered"]
        cancelled = [x for x in orders if x.status in {"cancelled", "expired"}]
        order_ids = {x.id for x in orders}
        delivered_ids = {x.id for x in delivered}
        delivered_customers = {x.customer_id for x in delivered}

        repeat_customers = 0
        if delivered_customers:
            counts: dict[UUID, int] = defaultdict(int)
            for order in delivered:
                counts[order.customer_id] += 1
            repeat_customers = sum(v >= 2 for v in counts.values())
        repeat_rate = (
            round(repeat_customers / len(delivered_customers) * 100, 2)
            if delivered_customers
            else 0.0
        )

        reviews = list(
            self.db.scalars(
                select(ReviewEntity).where(
                    ReviewEntity.order_id.in_(order_ids)
                )
            ).all()
        ) if order_ids else []
        average_rating = (
            round(sum(x.chef_overall for x in reviews) / len(reviews), 2)
            if reviews
            else None
        )

        tasks = {
            x.order_id: x
            for x in self.db.scalars(
                select(DeliveryTaskEntity).where(
                    DeliveryTaskEntity.order_id.in_(delivered_ids)
                )
            ).all()
        } if delivered_ids else {}
        measurable = 0
        on_time = 0
        for order in delivered:
            task = tasks.get(order.id)
            if (
                task is None
                or task.delivered_at is None
                or order.promised_delivery_window_end_at is None
            ):
                continue
            measurable += 1
            if _aware(task.delivered_at) <= _aware(
                order.promised_delivery_window_end_at
            ):
                on_time += 1
        coverage = (
            round(measurable / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )
        on_time_rate = (
            round(on_time / measurable * 100, 2)
            if measurable
            else None
        )

        payments = list(
            self.db.scalars(
                select(PaymentEntity).where(
                    PaymentEntity.order_id.in_(order_ids),
                    PaymentEntity.status == "succeeded",
                )
            ).all()
        ) if order_ids else []
        refunds = list(
            self.db.scalars(
                select(RefundEntity).where(
                    RefundEntity.order_id.in_(order_ids),
                    RefundEntity.status == "succeeded",
                )
            ).all()
        ) if order_ids else []
        tickets = list(
            self.db.scalars(
                select(SupportTicketEntity).where(
                    SupportTicketEntity.order_id.in_(order_ids)
                )
            ).all()
        ) if order_ids else []

        captured = sum(x.amount_minor for x in payments)
        refunded = sum(x.amount_minor for x in refunds)
        cancellation_rate = (
            round(len(cancelled) / len(orders) * 100, 2)
            if orders
            else 0.0
        )
        support_rate = (
            round(len(tickets) / len(orders) * 100, 2)
            if orders
            else 0.0
        )
        refund_rate = (
            round(len({x.order_id for x in refunds}) / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )

        stability = self.stability_report(program_id)
        cohort = self.cohort_report(program_id, max_weeks=8)

        def weighted(offset: int) -> float | None:
            numerator = 0
            denominator = 0
            for row in cohort.cohorts:
                cell = next(
                    (x for x in row.retention if x.week_offset == offset),
                    None,
                )
                if cell is None:
                    continue
                numerator += cell.active_customers
                denominator += row.cohort_size
            return (
                round(numerator / denominator * 100, 2)
                if denominator
                else None
            )

        active_critical_incidents = int(
            self.db.scalar(
                select(func.count(OperationsIncidentEntity.id)).where(
                    OperationsIncidentEntity.status.in_(["open", "acknowledged"]),
                    OperationsIncidentEntity.severity == "critical",
                )
            )
            or 0
        )
        open_payment_reconciliation = int(
            self.db.scalar(
                select(func.count(PaymentReconciliationIssueEntity.id)).where(
                    PaymentReconciliationIssueEntity.status == "open"
                )
            )
            or 0
        )

        # Sprint 46 replaces the manual profitability claim with
        # backend-calculated operational economics. Local import avoids
        # module initialization cycles with expansion assessment.
        from app.modules.operational_economics.service import (
            OperationalEconomicsService,
        )

        economics = OperationalEconomicsService(
            self.db,
            self.settings,
        ).report(program.id)

        evidence_rows = {
            x.evidence_type: x
            for x in self.db.scalars(
                select(PilotQaEvidenceEntity).where(
                    PilotQaEvidenceEntity.program_id == program.id
                )
            ).all()
        }
        statuses = {
            key: evidence_rows[key].status if key in evidence_rows else "missing"
            for key in MANDATORY_SCALE_EVIDENCE
        }

        blockers: list[str] = []
        if program.status != "completed":
            blockers.append("pilot_program_not_completed")
        if not stability.stability_gate_met:
            blockers.append("eight_week_stability_gate_not_met")
        if not economics.economics_evaluable:
            blockers.extend(
                f"economics_{x}" for x in economics.blockers
            )
        if economics.operational_profit_positive is not True:
            blockers.append("backend_operational_profit_not_positive")
        for key in MANDATORY_SCALE_EVIDENCE:
            if statuses[key] != "passed":
                blockers.append(f"evidence_{key}_{statuses[key]}")
        if active_critical_incidents:
            blockers.append("active_critical_incidents_present")
        if open_payment_reconciliation:
            blockers.append("open_payment_reconciliation_issues_present")
        blockers = list(dict.fromkeys(blockers))

        return PilotPostPilotReport(
            program=PilotProgramResponse.model_validate(program),
            generated_at=utc_now(),
            duration_days=(end_day - program.start_date).days + 1,
            orders_created=len(orders),
            delivered_orders=len(delivered),
            cancelled_orders=len(cancelled),
            cancellation_rate_pct=cancellation_rate,
            gmv_minor=sum(x.total_minor for x in delivered),
            captured_minor=captured,
            refunded_minor=refunded,
            net_collected_minor=max(0, captured - refunded),
            average_order_value_minor=(
                round(sum(x.total_minor for x in delivered) / len(delivered))
                if delivered
                else 0
            ),
            unique_delivered_customers=len(delivered_customers),
            repeat_customer_rate_pct=repeat_rate,
            average_chef_rating=average_rating,
            reviews_count=len(reviews),
            on_time_delivery_rate_pct=on_time_rate,
            delivery_promise_coverage_pct=coverage,
            support_tickets=len(tickets),
            support_tickets_per_100_orders=support_rate,
            refunds_count=len(refunds),
            refund_rate_pct=refund_rate,
            active_critical_incidents=active_critical_incidents,
            open_payment_reconciliation_issues=open_payment_reconciliation,
            acquired_customer_cohorts=len(cohort.cohorts),
            weighted_w1_retention_pct=weighted(1),
            weighted_w4_retention_pct=weighted(4),
            stability_gate_met=stability.stability_gate_met,
            current_consecutive_passed_weeks=(
                stability.current_consecutive_passed_weeks
            ),
            required_stability_weeks=program.required_stability_weeks,
            profitability_calculated_from_backend=True,
            operational_profit_evidence_status=(
                "backend_passed"
                if economics.operational_profit_positive is True
                else "backend_failed"
                if economics.operational_profit_positive is False
                else "backend_unevaluable"
            ),
            qa_exit_evidence_status=statuses["pilot_qa_exit"],
            operations_signoff_status=statuses["operations_signoff"],
            scale_ready=not blockers,
            scale_blockers=blockers,
        )
