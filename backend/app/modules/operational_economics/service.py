from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    EconomicsCostEntryEntity,
    ExpansionAssessmentEntity,
    ExpansionZoneEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    PaymentEntity,
    PilotProgramEntity,
    ZoneTrafficPolicyEntity,
    RefundEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.operational_economics.schemas import (
    CostBreakdownItem,
    CostEntryCreate,
    CostEntryResponse,
    EconomicsReport,
    ExpansionAssessmentResponse,
    ExpansionZoneCreate,
    ExpansionZoneDetail,
    ExpansionZoneResponse,
    VARIABLE_COST_TYPES,
)


def _bounds(start_day: date, end_day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_day, time.min, tzinfo=timezone.utc),
        datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


class OperationalEconomicsService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    def required_cost_types(self) -> list[str]:
        return [
            x.strip()
            for x in self.settings.economics_required_order_cost_types.split(",")
            if x.strip()
        ]

    def _program(self, program_id: UUID) -> PilotProgramEntity:
        row = self.db.get(PilotProgramEntity, program_id)
        if row is None:
            raise ApiError(
                404,
                "pilot_program_not_found",
                "برنامج الطيار غير موجود.",
            )
        return row

    def _period(
        self,
        program: PilotProgramEntity,
    ) -> tuple[date, date]:
        today = utc_now().date()
        end = min(today, program.end_date) if program.end_date else today
        if end < program.start_date:
            end = program.start_date
        return program.start_date, end

    def _orders(
        self,
        program: PilotProgramEntity,
        start_day: date,
        end_day: date,
    ) -> list[OrderEntity]:
        start_dt, end_dt = _bounds(start_day, end_day)
        stmt = select(OrderEntity).where(
            OrderEntity.created_at >= start_dt,
            OrderEntity.created_at < end_dt,
        )
        if program.area:
            stmt = (
                stmt.join(
                    OrderDeliveryAddressEntity,
                    OrderDeliveryAddressEntity.order_id == OrderEntity.id,
                )
                .where(OrderDeliveryAddressEntity.area == program.area)
            )
        return list(self.db.scalars(stmt).all())

    def create_cost(
        self,
        *,
        payload: CostEntryCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> CostEntryResponse:
        program = None
        if payload.pilot_program_id:
            program = self._program(payload.pilot_program_id)

        order = None
        if payload.order_id:
            order = self.db.get(OrderEntity, payload.order_id)
            if order is None:
                raise ApiError(
                    404,
                    "economics_order_not_found",
                    "الطلب المرتبط بالتكلفة غير موجود.",
                )

        if (
            payload.external_reference
            and self.db.scalar(
                select(EconomicsCostEntryEntity).where(
                    EconomicsCostEntryEntity.source == payload.source,
                    EconomicsCostEntryEntity.external_reference
                    == payload.external_reference,
                )
            )
            is not None
        ):
            raise ApiError(
                409,
                "economics_external_reference_exists",
                "مرجع التكلفة الخارجي مسجل بالفعل.",
            )

        if order is not None and program is not None:
            start, end = self._period(program)
            if not (start <= payload.incurred_on <= end):
                raise ApiError(
                    409,
                    "economics_cost_outside_program",
                    "تاريخ التكلفة خارج فترة برنامج الطيار.",
                )

        cost_scope = (
            "fixed"
            if payload.cost_type == "fixed_operations"
            else "variable"
        )
        area = (payload.area or "").strip() or (
            program.area if program else None
        )
        row = EconomicsCostEntryEntity(
            pilot_program_id=payload.pilot_program_id,
            order_id=payload.order_id,
            area=area,
            incurred_on=payload.incurred_on,
            cost_type=payload.cost_type,
            cost_scope=cost_scope,
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            source=payload.source,
            external_reference=(
                payload.external_reference or ""
            ).strip()
            or None,
            note=payload.note,
            created_by_admin_id=admin_id,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.add(
            action="economics.cost.created",
            actor_user_id=admin_id,
            entity_type="economics_cost_entry",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "program_id": (
                    str(row.pilot_program_id)
                    if row.pilot_program_id
                    else None
                ),
                "order_id": str(row.order_id) if row.order_id else None,
                "cost_type": row.cost_type,
                "amount_minor": row.amount_minor,
                "source": row.source,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return CostEntryResponse.model_validate(row)

    def verify_cost(
        self,
        *,
        cost_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> CostEntryResponse:
        row = self.db.get(EconomicsCostEntryEntity, cost_id)
        if row is None:
            raise ApiError(
                404,
                "economics_cost_not_found",
                "قيد التكلفة غير موجود.",
            )
        if not row.is_verified:
            row.is_verified = True
            row.verified_by_admin_id = admin_id
            row.verified_at = utc_now()
            self.audit.add(
                action="economics.cost.verified",
                actor_user_id=admin_id,
                entity_type="economics_cost_entry",
                entity_id=str(row.id),
                request_id=request_id,
                metadata={
                    "cost_type": row.cost_type,
                    "amount_minor": row.amount_minor,
                },
            )
            self.db.commit()
            self.db.refresh(row)
        return CostEntryResponse.model_validate(row)

    def costs(
        self,
        *,
        program_id: UUID | None,
        order_id: UUID | None,
        verified: bool | None,
        limit: int,
    ) -> list[CostEntryResponse]:
        stmt = select(EconomicsCostEntryEntity)
        if program_id:
            stmt = stmt.where(
                EconomicsCostEntryEntity.pilot_program_id == program_id
            )
        if order_id:
            stmt = stmt.where(EconomicsCostEntryEntity.order_id == order_id)
        if verified is not None:
            stmt = stmt.where(
                EconomicsCostEntryEntity.is_verified.is_(verified)
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(
                    EconomicsCostEntryEntity.incurred_on.desc(),
                    EconomicsCostEntryEntity.created_at.desc(),
                ).limit(limit)
            ).all()
        )
        return [CostEntryResponse.model_validate(x) for x in rows]

    def report(
        self,
        program_id: UUID,
    ) -> EconomicsReport:
        program = self._program(program_id)
        start_day, end_day = self._period(program)
        orders = self._orders(program, start_day, end_day)
        delivered = [x for x in orders if x.status == "delivered"]
        delivered_ids = {x.id for x in delivered}
        all_ids = {x.id for x in orders}

        payments = (
            list(
                self.db.scalars(
                    select(PaymentEntity).where(
                        PaymentEntity.order_id.in_(all_ids),
                        PaymentEntity.status == "succeeded",
                    )
                ).all()
            )
            if all_ids
            else []
        )
        refunds = (
            list(
                self.db.scalars(
                    select(RefundEntity).where(
                        RefundEntity.order_id.in_(all_ids),
                        RefundEntity.status == "succeeded",
                    )
                ).all()
            )
            if all_ids
            else []
        )
        paid_order_ids = {x.order_id for x in payments}
        succeeded_payment_orders = len(delivered_ids & paid_order_ids)

        start_dt, end_dt = _bounds(start_day, end_day)
        cost_stmt = select(EconomicsCostEntryEntity).where(
            EconomicsCostEntryEntity.incurred_on >= start_day,
            EconomicsCostEntryEntity.incurred_on <= end_day,
        )
        # Explicit program costs always belong to the program. Unscoped
        # costs may participate only when their area matches the program.
        if program.area:
            cost_stmt = cost_stmt.where(
                (EconomicsCostEntryEntity.pilot_program_id == program.id)
                | (
                    (EconomicsCostEntryEntity.pilot_program_id.is_(None))
                    & (EconomicsCostEntryEntity.area == program.area)
                )
            )
        else:
            cost_stmt = cost_stmt.where(
                EconomicsCostEntryEntity.pilot_program_id == program.id
            )

        cost_rows = list(self.db.scalars(cost_stmt).all())
        verified_rows = [x for x in cost_rows if x.is_verified]
        unverified_count = sum(not x.is_verified for x in cost_rows)

        variable = [
            x for x in verified_rows if x.cost_scope == "variable"
        ]
        fixed = [x for x in verified_rows if x.cost_scope == "fixed"]

        breakdown: dict[str, int] = defaultdict(int)
        for row in verified_rows:
            breakdown[row.cost_type] += row.amount_minor

        required = self.required_cost_types()
        by_order: dict[UUID, set[str]] = defaultdict(set)
        for row in verified_rows:
            if (
                row.order_id is not None
                and row.order_id in delivered_ids
                and row.cost_type in required
            ):
                by_order[row.order_id].add(row.cost_type)
        fully_costed = sum(
            all(kind in by_order[order.id] for kind in required)
            for order in delivered
        )

        captured = sum(x.amount_minor for x in payments)
        refunded = sum(x.amount_minor for x in refunds)
        net_collected = captured - refunded
        variable_cost = sum(x.amount_minor for x in variable)
        fixed_cost = sum(x.amount_minor for x in fixed)
        contribution = net_collected - variable_cost
        operating_profit = contribution - fixed_cost

        revenue_coverage = (
            round(succeeded_payment_orders / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )
        cost_coverage = (
            round(fully_costed / len(delivered) * 100, 2)
            if delivered
            else 0.0
        )
        contribution_margin = (
            round(contribution / net_collected * 100, 2)
            if net_collected > 0
            else None
        )
        operating_margin = (
            round(operating_profit / net_collected * 100, 2)
            if net_collected > 0
            else None
        )

        blockers: list[str] = []
        if not delivered:
            blockers.append("no_delivered_orders")
        if revenue_coverage < 100.0:
            blockers.append("revenue_coverage_below_100_pct")
        if cost_coverage < 100.0:
            blockers.append("cost_coverage_below_100_pct")
        if unverified_count:
            blockers.append("unverified_cost_entries_present")
        if net_collected <= 0:
            blockers.append("net_collected_not_positive")

        evaluable = not blockers
        return EconomicsReport(
            program_id=program.id,
            area=program.area,
            period_start=start_day,
            period_end=end_day,
            delivered_orders=len(delivered),
            delivered_gmv_minor=sum(x.total_minor for x in delivered),
            succeeded_payment_orders=succeeded_payment_orders,
            captured_minor=captured,
            refunded_minor=refunded,
            net_collected_minor=net_collected,
            revenue_coverage_pct=revenue_coverage,
            variable_cost_minor=variable_cost,
            fixed_cost_minor=fixed_cost,
            contribution_minor=contribution,
            contribution_margin_pct=contribution_margin,
            contribution_per_delivered_order_minor=(
                round(contribution / len(delivered))
                if delivered
                else None
            ),
            operational_profit_minor=operating_profit,
            operational_profit_margin_pct=operating_margin,
            required_order_cost_types=required,
            fully_costed_delivered_orders=fully_costed,
            cost_coverage_pct=cost_coverage,
            unverified_cost_entries=unverified_count,
            cost_breakdown=[
                CostBreakdownItem(
                    cost_type=kind,
                    amount_minor=amount,
                )
                for kind, amount in sorted(breakdown.items())
            ],
            economics_evaluable=evaluable,
            operational_profit_positive=(
                operating_profit > 0 if evaluable else None
            ),
            blockers=blockers,
            generated_at=utc_now(),
        )

    # ------------------------------------------------------
    # Expansion zones
    # ------------------------------------------------------
    def create_zone(
        self,
        *,
        payload: ExpansionZoneCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> ExpansionZoneResponse:
        program = self._program(payload.source_program_id)
        area = payload.area.strip()
        if self.db.scalar(
            select(ExpansionZoneEntity).where(
                func.lower(ExpansionZoneEntity.area)
                == area.lower()
            )
        ) is not None:
            raise ApiError(
                409,
                "expansion_zone_exists",
                "منطقة التوسع مسجلة بالفعل.",
            )
        row = ExpansionZoneEntity(
            area=area,
            source_program_id=program.id,
            min_delivered_orders=(
                payload.min_delivered_orders
                or self.settings.economics_default_min_delivered_orders
            ),
            min_contribution_margin_pct=(
                payload.min_contribution_margin_pct
                if payload.min_contribution_margin_pct is not None
                else self.settings.economics_default_min_contribution_margin_pct
            ),
            min_operational_profit_minor=(
                payload.min_operational_profit_minor
            ),
            notes=payload.notes,
            created_by_admin_id=admin_id,
        )
        self.db.add(row)
        self.db.flush()
        self.db.add(
            ZoneTrafficPolicyEntity(
                zone_id=row.id,
                is_enabled=True,
                hourly_order_cap=self.settings.traffic_default_hourly_order_cap,
                chef_daily_order_cap=self.settings.traffic_default_chef_daily_order_cap,
                enforce_rollout_bucket=True,
                warning_utilization_pct=self.settings.traffic_warning_utilization_pct,
                critical_utilization_pct=self.settings.traffic_critical_utilization_pct,
                rejection_spike_pct=self.settings.traffic_rejection_spike_pct,
                rejection_spike_min_attempts=self.settings.traffic_rejection_spike_min_attempts,
                note="Created with Expansion Zone",
                created_by_admin_id=admin_id,
                updated_by_admin_id=admin_id,
            )
        )
        self.audit.add(
            action="expansion.zone.created",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "area": row.area,
                "source_program_id": str(row.source_program_id),
                "min_delivered_orders": row.min_delivered_orders,
                "min_contribution_margin_pct": row.min_contribution_margin_pct,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return ExpansionZoneResponse.model_validate(row)

    def zones(self) -> list[ExpansionZoneDetail]:
        rows = list(
            self.db.scalars(
                select(ExpansionZoneEntity).order_by(
                    ExpansionZoneEntity.created_at.desc()
                )
            ).all()
        )
        return [self.zone_detail(x.id) for x in rows]

    def _zone(self, zone_id: UUID) -> ExpansionZoneEntity:
        row = self.db.get(ExpansionZoneEntity, zone_id)
        if row is None:
            raise ApiError(
                404,
                "expansion_zone_not_found",
                "منطقة التوسع غير موجودة.",
            )
        return row

    def latest_assessment(
        self,
        zone_id: UUID,
    ) -> ExpansionAssessmentEntity | None:
        return self.db.scalar(
            select(ExpansionAssessmentEntity)
            .where(ExpansionAssessmentEntity.zone_id == zone_id)
            .order_by(ExpansionAssessmentEntity.generated_at.desc())
        )

    def zone_detail(self, zone_id: UUID) -> ExpansionZoneDetail:
        zone = self._zone(zone_id)
        assessment = self.latest_assessment(zone.id)
        return ExpansionZoneDetail(
            zone=ExpansionZoneResponse.model_validate(zone),
            latest_assessment=(
                ExpansionAssessmentResponse.model_validate(assessment)
                if assessment
                else None
            ),
        )

    def assess_zone(
        self,
        *,
        zone_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> ExpansionAssessmentResponse:
        zone = self._zone(zone_id)
        program = self._program(zone.source_program_id)
        economics = self.report(program.id)

        # Local import prevents an import cycle: Pilot stability calls the
        # economics report when producing the post-pilot profitability gate.
        from app.modules.pilot_stability.service import PilotStabilityService

        pilot_service = PilotStabilityService(self.db, self.settings)
        stability = pilot_service.stability_report(program.id)
        post = pilot_service.post_pilot_report(program.id)

        blockers: list[str] = []
        if program.status != "completed":
            blockers.append("source_pilot_not_completed")
        if not economics.economics_evaluable:
            blockers.extend(
                f"economics_{x}" for x in economics.blockers
            )
        if economics.operational_profit_positive is not True:
            blockers.append("operational_profit_not_positive")
        if economics.delivered_orders < zone.min_delivered_orders:
            blockers.append(
                f"delivered_orders_{economics.delivered_orders}_below_"
                f"{zone.min_delivered_orders}"
            )
        if (
            economics.contribution_margin_pct is None
            or economics.contribution_margin_pct
            < zone.min_contribution_margin_pct
        ):
            blockers.append("contribution_margin_below_zone_target")
        if (
            economics.operational_profit_minor
            < zone.min_operational_profit_minor
        ):
            blockers.append("operational_profit_below_zone_target")
        if not stability.stability_gate_met:
            blockers.append("eight_week_stability_gate_not_met")
        if not post.scale_ready:
            blockers.extend(
                f"post_pilot_{x}" for x in post.scale_blockers
            )

        # Deduplicate blockers without hiding their source.
        blockers = list(dict.fromkeys(blockers))
        decision = "ready" if not blockers else "blocked"
        row = ExpansionAssessmentEntity(
            zone_id=zone.id,
            program_id=program.id,
            period_start=economics.period_start,
            period_end=economics.period_end,
            delivered_orders=economics.delivered_orders,
            net_collected_minor=economics.net_collected_minor,
            variable_cost_minor=economics.variable_cost_minor,
            contribution_minor=economics.contribution_minor,
            contribution_margin_pct=economics.contribution_margin_pct,
            fixed_cost_minor=economics.fixed_cost_minor,
            operational_profit_minor=economics.operational_profit_minor,
            cost_coverage_pct=economics.cost_coverage_pct,
            revenue_coverage_pct=economics.revenue_coverage_pct,
            unverified_cost_entries=economics.unverified_cost_entries,
            economics_evaluable=economics.economics_evaluable,
            stability_gate_met=stability.stability_gate_met,
            post_pilot_scale_ready=post.scale_ready,
            decision=decision,
            blockers_json=blockers,
            generated_by_admin_id=admin_id,
        )
        self.db.add(row)
        if decision == "ready" and zone.status == "candidate":
            zone.status = "ready"
        elif decision == "blocked" and zone.status == "ready":
            zone.status = "candidate"
        self.audit.add(
            action="expansion.zone.assessed",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={
                "decision": decision,
                "blockers": blockers,
                "contribution_margin_pct": economics.contribution_margin_pct,
                "operational_profit_minor": economics.operational_profit_minor,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return ExpansionAssessmentResponse.model_validate(row)

    def approve_zone(
        self,
        *,
        zone_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> ExpansionZoneResponse:
        zone = self._zone(zone_id)
        latest = self.latest_assessment(zone.id)
        if latest is None or latest.decision != "ready":
            raise ApiError(
                409,
                "expansion_zone_not_ready",
                "لا يمكن اعتماد المنطقة قبل اجتياز تقييم التوسع.",
            )
        zone.status = "approved"
        zone.approved_by_admin_id = admin_id
        zone.approved_at = utc_now()
        self.audit.add(
            action="expansion.zone.approved",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={"assessment_id": str(latest.id)},
        )
        self.db.commit()
        self.db.refresh(zone)
        return ExpansionZoneResponse.model_validate(zone)

    def launch_zone(
        self,
        *,
        zone_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> ExpansionZoneResponse:
        zone = self._zone(zone_id)
        if self.settings.expansion_rollout_required:
            raise ApiError(
                409,
                "expansion_rollout_required",
                "Pilot/production launch must use the controlled rollout endpoints.",
            )
        if zone.status != "approved":
            raise ApiError(
                409,
                "expansion_zone_not_approved",
                "المنطقة يجب أن تكون معتمدة قبل التشغيل.",
            )
        latest = self.assess_zone(
            zone_id=zone.id,
            admin_id=admin_id,
            request_id=request_id,
        )
        if latest.decision != "ready":
            raise ApiError(
                409,
                "expansion_zone_readiness_changed",
                "حالة الجاهزية تغيرت؛ لا يمكن تشغيل المنطقة.",
            )
        zone = self._zone(zone.id)
        zone.status = "live"
        zone.launched_at = utc_now()
        zone.paused_at = None
        zone.rollout_stage = "full"
        zone.rollout_percent = 100
        zone.rollout_started_at = zone.rollout_started_at or utc_now()
        zone.rollout_completed_at = utc_now()
        self.audit.add(
            action="expansion.zone.launched",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={"assessment_id": str(latest.id)},
        )
        self.db.commit()
        self.db.refresh(zone)
        return ExpansionZoneResponse.model_validate(zone)

    def pause_zone(
        self,
        *,
        zone_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> ExpansionZoneResponse:
        zone = self._zone(zone_id)
        if zone.status != "live":
            raise ApiError(
                409,
                "expansion_zone_not_live",
                "يمكن إيقاف منطقة تعمل فقط.",
            )
        zone.status = "paused"
        zone.paused_at = utc_now()
        zone.rollout_stage = "paused"
        self.audit.add(
            action="expansion.zone.paused",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(zone)
        return ExpansionZoneResponse.model_validate(zone)
