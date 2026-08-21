from __future__ import annotations

import base64
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    EconomicsCostEntryEntity,
    ExpansionAssessmentEntity,
    ExpansionRolloutEventEntity,
    ExpansionZoneBudgetEntity,
    ExpansionZoneEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    PaymentEntity,
    PaymentProviderTransactionEntity,
    PaymentReconciliationIssueEntity,
    PilotProgramEntity,
    ProviderCostImportBatchEntity,
    ProviderCostImportLineEntity,
    ProviderSettlementBatchEntity,
    LaunchCommandEventEntity,
    LaunchCommandSessionEntity,
    ProviderSettlementLineEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.financial_automation.schemas import (
    ProviderCostImportBatchResponse,
    ProviderCostImportCreate,
    ProviderCostImportDetail,
    ProviderCostLineInput,
    ProviderCostImportLineResponse,
    RolloutRequest,
    RolloutEventResponse,
    RolloutResponse,
    SettlementBatchCreate,
    SettlementBatchDetail,
    SettlementBatchResponse,
    SettlementLineResponse,
    TwilioUsageSyncRequest,
    ZoneBudgetMovement,
    ZoneBudgetResponse,
    ZoneBudgetSummary,
    ZoneBudgetUpsert,
)
from app.modules.operational_economics.service import OperationalEconomicsService


def _canonical_hash(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class FinancialAutomationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)
        self.economics = OperationalEconomicsService(db, settings)

    # ------------------------------------------------------------------
    # Shared lookups
    # ------------------------------------------------------------------
    def _program(self, program_id: UUID | None) -> PilotProgramEntity | None:
        if program_id is None:
            return None
        row = self.db.get(PilotProgramEntity, program_id)
        if row is None:
            raise ApiError(
                404,
                "pilot_program_not_found",
                "برنامج الطيار غير موجود.",
            )
        return row

    def _zone(self, zone_id: UUID) -> ExpansionZoneEntity:
        row = self.db.get(ExpansionZoneEntity, zone_id)
        if row is None:
            raise ApiError(
                404,
                "expansion_zone_not_found",
                "منطقة التوسع غير موجودة.",
            )
        return row

    @staticmethod
    def _egp_minor(
        source_minor: int,
        source_currency: str,
        fx_rate_to_egp: float | None,
    ) -> int:
        if source_currency.upper() == "EGP":
            return source_minor
        if fx_rate_to_egp is None or fx_rate_to_egp <= 0:
            raise ApiError(
                409,
                "provider_import_fx_required",
                "سعر التحويل إلى EGP مطلوب للتكلفة بعملة أجنبية.",
            )
        result = (
            Decimal(source_minor)
            * Decimal(str(fx_rate_to_egp))
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return max(1, int(result))

    # ------------------------------------------------------------------
    # Provider cost imports
    # ------------------------------------------------------------------
    def create_cost_import(
        self,
        *,
        payload: ProviderCostImportCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> ProviderCostImportDetail:
        if not payload.lines:
            raise ApiError(
                422,
                "provider_import_empty",
                "ملف التكلفة لا يحتوي على سطور.",
            )
        if len(payload.lines) > self.settings.provider_import_max_lines:
            raise ApiError(
                413,
                "provider_import_too_large",
                "عدد سطور الاستيراد أكبر من الحد المسموح.",
            )
        program = self._program(payload.pilot_program_id)
        existing = self.db.scalar(
            select(ProviderCostImportBatchEntity).where(
                ProviderCostImportBatchEntity.provider == payload.provider,
                ProviderCostImportBatchEntity.external_reference
                == payload.external_reference,
            )
        )
        if existing is not None:
            raise ApiError(
                409,
                "provider_import_reference_exists",
                "مرجع الاستيراد مسجل بالفعل.",
            )

        canonical = payload.model_dump(mode="json")
        batch = ProviderCostImportBatchEntity(
            provider=payload.provider,
            pilot_program_id=payload.pilot_program_id,
            area=(payload.area or "").strip() or (
                program.area if program else None
            ),
            period_start=payload.period_start,
            period_end=payload.period_end,
            source_currency=payload.source_currency,
            fx_rate_to_egp=payload.fx_rate_to_egp,
            fx_reference=(payload.fx_reference or "").strip() or None,
            external_reference=payload.external_reference.strip(),
            checksum_sha256=_canonical_hash(canonical),
            status="draft",
            created_by_admin_id=admin_id,
        )
        self.db.add(batch)
        self.db.flush()

        seen: set[str] = set()
        total_source = 0
        total_egp = 0
        for item in payload.lines:
            if item.line_key in seen:
                raise ApiError(
                    409,
                    "provider_import_duplicate_line_key",
                    f"line_key مكرر: {item.line_key}",
                )
            seen.add(item.line_key)
            egp_minor = self._egp_minor(
                item.source_amount_minor,
                payload.source_currency,
                payload.fx_rate_to_egp,
            )
            line = ProviderCostImportLineEntity(
                batch_id=batch.id,
                line_key=item.line_key,
                order_id=item.order_id,
                incurred_on=item.incurred_on,
                cost_type=item.cost_type,
                source_amount_minor=item.source_amount_minor,
                source_currency=payload.source_currency,
                egp_amount_minor=egp_minor,
                external_reference=item.external_reference,
                description=item.description,
                raw_json=item.raw_json,
            )
            self.db.add(line)
            total_source += item.source_amount_minor
            total_egp += egp_minor

        batch.rows_count = len(payload.lines)
        batch.total_source_minor = total_source
        batch.total_egp_minor = total_egp
        self.audit.add(
            action="economics.provider_import.created",
            actor_user_id=admin_id,
            entity_type="provider_cost_import_batch",
            entity_id=str(batch.id),
            request_id=request_id,
            metadata={
                "provider": batch.provider,
                "rows": batch.rows_count,
                "checksum_sha256": batch.checksum_sha256,
            },
        )
        self.db.commit()
        return self.cost_import_detail(batch.id)

    def _validate_import_line(
        self,
        *,
        batch: ProviderCostImportBatchEntity,
        line: ProviderCostImportLineEntity,
        program: PilotProgramEntity | None,
    ) -> list[str]:
        errors: list[str] = []
        if not (batch.period_start <= line.incurred_on <= batch.period_end):
            errors.append("line_date_outside_batch_period")

        if line.order_id is not None:
            order = self.db.get(OrderEntity, line.order_id)
            if order is None:
                errors.append("order_not_found")
            else:
                if program is not None:
                    if not (
                        program.start_date
                        <= line.incurred_on
                        <= (program.end_date or line.incurred_on)
                    ):
                        errors.append("line_outside_program_period")
                    if program.area:
                        address = self.db.get(
                            OrderDeliveryAddressEntity,
                            order.id,
                        )
                        if address is None or address.area != program.area:
                            errors.append("order_outside_program_area")

        return errors

    def _import_risk_flags(
        self,
        *,
        batch: ProviderCostImportBatchEntity,
        lines: list[ProviderCostImportLineEntity],
    ) -> list[str]:
        flags: list[str] = []
        if batch.source_currency != "EGP":
            flags.append("foreign_currency")
        if batch.pilot_program_id is None:
            flags.append("unscoped_pilot_program")
        if not (batch.area or "").strip():
            flags.append("unscoped_area")
        if batch.total_egp_minor >= self.settings.vendor_accounting_high_value_import_minor:
            flags.append("high_value_import")
        if any(x.cost_type == "fixed_operations" for x in lines):
            flags.append("fixed_operations")
        if any(x.cost_type == "provider_adjustment" for x in lines):
            flags.append("provider_adjustment")
        if any(
            x.order_id is None
            and x.cost_type not in {"fixed_operations", "cloud_infrastructure", "cloud_storage", "communications_provider"}
            for x in lines
        ):
            flags.append("unallocated_variable_cost")
        return list(dict.fromkeys(flags))

    def validate_cost_import(
        self,
        *,
        batch_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> ProviderCostImportDetail:
        batch = self.db.get(ProviderCostImportBatchEntity, batch_id)
        if batch is None:
            raise ApiError(404, "provider_import_not_found", "دفعة الاستيراد غير موجودة.")
        if batch.status == "applied":
            return self.cost_import_detail(batch.id)

        program = self._program(batch.pilot_program_id)
        lines = list(
            self.db.scalars(
                select(ProviderCostImportLineEntity)
                .where(ProviderCostImportLineEntity.batch_id == batch.id)
                .order_by(ProviderCostImportLineEntity.created_at.asc())
            ).all()
        )
        errors: list[dict] = []
        for line in lines:
            line_errors = self._validate_import_line(
                batch=batch,
                line=line,
                program=program,
            )
            if line_errors:
                errors.append(
                    {
                        "line_key": line.line_key,
                        "errors": line_errors,
                    }
                )

        if (
            batch.source_currency != "EGP"
            and (
                batch.fx_rate_to_egp is None
                or not (batch.fx_reference or "").strip()
            )
        ):
            errors.append(
                {
                    "batch": "fx",
                    "errors": ["fx_rate_and_reference_required"],
                }
            )

        batch.validation_errors_json = errors
        batch.risk_flags_json = self._import_risk_flags(
            batch=batch,
            lines=lines,
        )
        batch.status = "validated" if not errors else "failed"
        batch.validated_by_admin_id = admin_id
        batch.validated_at = utc_now()

        self.audit.add(
            action="economics.provider_import.validated",
            actor_user_id=admin_id,
            entity_type="provider_cost_import_batch",
            entity_id=str(batch.id),
            request_id=request_id,
            metadata={
                "status": batch.status,
                "errors": len(errors),
            },
        )
        self.db.commit()
        return self.cost_import_detail(batch.id)

    def apply_cost_import(
        self,
        *,
        batch_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> ProviderCostImportDetail:
        batch = self.db.get(ProviderCostImportBatchEntity, batch_id)
        if batch is None:
            raise ApiError(404, "provider_import_not_found", "دفعة الاستيراد غير موجودة.")
        if batch.status == "applied":
            return self.cost_import_detail(batch.id)
        if batch.status != "validated":
            raise ApiError(
                409,
                "provider_import_not_validated",
                "يجب أن تجتاز الدفعة التحقق قبل تطبيقها.",
            )
        if self.settings.vendor_accounting_require_dual_control:
            if batch.review_status != "approved":
                raise ApiError(
                    409,
                    "provider_import_review_required",
                    "يجب اعتماد الدفعة من مراجعة محاسبية مستقلة قبل تطبيقها.",
                )
            if (
                batch.created_by_admin_id is not None
                and batch.reviewed_by_admin_id == batch.created_by_admin_id
            ):
                raise ApiError(
                    409,
                    "vendor_accounting_dual_control_required",
                    "منشئ الدفعة لا يمكنه اعتمادها في وضع maker-checker.",
                )

        lines = list(
            self.db.scalars(
                select(ProviderCostImportLineEntity).where(
                    ProviderCostImportLineEntity.batch_id == batch.id
                )
            ).all()
        )
        applied = 0
        for line in lines:
            if line.applied_cost_entry_id is not None:
                continue
            external_reference = (
                f"provider-import:{batch.provider}:"
                f"{batch.external_reference}:{line.line_key}"
            )
            existing = self.db.scalar(
                select(EconomicsCostEntryEntity).where(
                    EconomicsCostEntryEntity.source == "provider",
                    EconomicsCostEntryEntity.external_reference
                    == external_reference,
                )
            )
            if existing is not None:
                line.applied_cost_entry_id = existing.id
                continue

            scope = (
                "fixed"
                if line.cost_type == "fixed_operations"
                else "variable"
            )
            cost = EconomicsCostEntryEntity(
                pilot_program_id=batch.pilot_program_id,
                order_id=line.order_id,
                area=batch.area,
                incurred_on=line.incurred_on,
                cost_type=line.cost_type,
                cost_scope=scope,
                amount_minor=line.egp_amount_minor,
                currency="EGP",
                source="provider",
                external_reference=external_reference,
                note=(
                    line.description
                    or f"{batch.provider} provider import"
                ),
                is_verified=True,
                verified_by_admin_id=admin_id,
                verified_at=utc_now(),
                created_by_admin_id=admin_id,
            )
            self.db.add(cost)
            self.db.flush()
            line.applied_cost_entry_id = cost.id
            applied += 1

        batch.status = "applied"
        batch.applied_by_admin_id = admin_id
        batch.applied_at = utc_now()
        batch.applied_cost_entries = sum(
            x.applied_cost_entry_id is not None for x in lines
        )
        self.audit.add(
            action="economics.provider_import.applied",
            actor_user_id=admin_id,
            entity_type="provider_cost_import_batch",
            entity_id=str(batch.id),
            request_id=request_id,
            metadata={
                "applied_now": applied,
                "applied_total": batch.applied_cost_entries,
            },
        )
        self.db.commit()
        return self.cost_import_detail(batch.id)

    def cost_import_detail(self, batch_id: UUID) -> ProviderCostImportDetail:
        batch = self.db.get(ProviderCostImportBatchEntity, batch_id)
        if batch is None:
            raise ApiError(404, "provider_import_not_found", "دفعة الاستيراد غير موجودة.")
        lines = list(
            self.db.scalars(
                select(ProviderCostImportLineEntity)
                .where(ProviderCostImportLineEntity.batch_id == batch.id)
                .order_by(ProviderCostImportLineEntity.created_at.asc())
            ).all()
        )
        return ProviderCostImportDetail(
            batch=ProviderCostImportBatchResponse.model_validate(batch),
            lines=[
                ProviderCostImportLineResponse.model_validate(x)
                for x in lines
            ],
        )

    def cost_imports(
        self,
        *,
        provider: str | None,
        status: str | None,
        limit: int,
    ) -> list[ProviderCostImportBatchResponse]:
        stmt = select(ProviderCostImportBatchEntity)
        if provider:
            stmt = stmt.where(
                ProviderCostImportBatchEntity.provider
                == provider.strip().lower()
            )
        if status:
            stmt = stmt.where(
                ProviderCostImportBatchEntity.status == status
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(
                    ProviderCostImportBatchEntity.created_at.desc()
                ).limit(limit)
            ).all()
        )
        return [
            ProviderCostImportBatchResponse.model_validate(x)
            for x in rows
        ]

    # ------------------------------------------------------------------
    # Twilio Usage Records adapter
    # ------------------------------------------------------------------
    def sync_twilio_usage(
        self,
        *,
        payload: TwilioUsageSyncRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> ProviderCostImportDetail:
        if not self.settings.twilio_account_sid.strip():
            raise ApiError(
                409,
                "twilio_account_not_configured",
                "Twilio Account SID غير مضبوط.",
            )
        if not self.settings.twilio_auth_token.strip():
            raise ApiError(
                409,
                "twilio_auth_not_configured",
                "Twilio Auth Token غير مضبوط.",
            )

        params = urllib.parse.urlencode(
            {
                "Category": payload.category,
                "StartDate": payload.period_start.isoformat(),
                "EndDate": payload.period_end.isoformat(),
                "IncludeSubaccounts": "false",
                "PageSize": "1000",
            }
        )
        url = (
            self.settings.twilio_api_base_url.rstrip("/")
            + f"/Accounts/{self.settings.twilio_account_sid}/"
            + f"Usage/Records.json?{params}"
        )
        token = base64.b64encode(
            (
                f"{self.settings.twilio_account_sid}:"
                f"{self.settings.twilio_auth_token}"
            ).encode("utf-8")
        ).decode("ascii")
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Basic {token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                req,
                timeout=self.settings.provider_import_request_timeout_seconds,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ApiError(
                502,
                "twilio_usage_fetch_failed",
                "تعذر جلب سجل استخدام Twilio.",
            ) from exc

        records = data.get("usage_records")
        if not isinstance(records, list):
            raise ApiError(
                502,
                "twilio_usage_shape_invalid",
                "استجابة Twilio Usage Records غير متوقعة.",
            )

        inputs: list[ProviderCostLineInput] = []
        currencies: set[str] = set()
        for index, record in enumerate(records):
            try:
                price = abs(Decimal(str(record.get("price") or "0")))
            except Exception:
                continue
            if price <= 0:
                continue
            currency = str(record.get("price_unit") or "").upper()
            if len(currency) != 3:
                raise ApiError(
                    502,
                    "twilio_usage_currency_invalid",
                    "عملة تكلفة Twilio غير صالحة.",
                )
            currencies.add(currency)
            source_minor = int(
                (price * Decimal("100")).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP,
                )
            )
            inputs.append(
                ProviderCostLineInput(
                    line_key=(
                        f"{record.get('category') or payload.category}:"
                        f"{record.get('start_date') or payload.period_start}:"
                        f"{record.get('end_date') or payload.period_end}:"
                        f"{index}"
                    ),
                    incurred_on=payload.period_end,
                    cost_type="communications_provider",
                    source_amount_minor=source_minor,
                    external_reference=(
                        str(record.get("uri") or "")[:220] or None
                    ),
                    description=(
                        str(record.get("description") or "Twilio usage")
                    ),
                    raw_json=record,
                )
            )

        if not inputs:
            raise ApiError(
                409,
                "twilio_usage_no_billable_cost",
                "لم ترجع Twilio تكلفة قابلة للاستيراد للفترة.",
            )
        if len(currencies) != 1:
            raise ApiError(
                409,
                "twilio_usage_multiple_currencies",
                "دفعة Twilio تحتوي أكثر من عملة.",
            )

        source_currency = next(iter(currencies))
        create = ProviderCostImportCreate(
            provider="twilio",
            pilot_program_id=payload.pilot_program_id,
            area=payload.area,
            period_start=payload.period_start,
            period_end=payload.period_end,
            source_currency=source_currency,
            fx_rate_to_egp=payload.fx_rate_to_egp,
            fx_reference=payload.fx_reference,
            external_reference=payload.external_reference,
            lines=inputs,
        )
        return self.create_cost_import(
            payload=create,
            admin_id=admin_id,
            request_id=request_id,
        )

    # ------------------------------------------------------------------
    # Paymob settlement reconciliation
    # ------------------------------------------------------------------
    def create_settlement(
        self,
        *,
        payload: SettlementBatchCreate,
        admin_id: UUID,
        request_id: str | None,
    ) -> SettlementBatchDetail:
        if not payload.lines:
            raise ApiError(
                422,
                "settlement_empty",
                "دفعة التسوية لا تحتوي على معاملات.",
            )
        if len(payload.lines) > self.settings.provider_import_max_lines:
            raise ApiError(
                413,
                "settlement_too_large",
                "عدد معاملات التسوية أكبر من الحد المسموح.",
            )
        self._program(payload.pilot_program_id)
        existing = self.db.scalar(
            select(ProviderSettlementBatchEntity).where(
                ProviderSettlementBatchEntity.provider
                == payload.provider,
                ProviderSettlementBatchEntity.external_reference
                == payload.external_reference,
            )
        )
        if existing is not None:
            raise ApiError(
                409,
                "settlement_reference_exists",
                "مرجع التسوية مسجل بالفعل.",
            )
        batch = ProviderSettlementBatchEntity(
            provider=payload.provider,
            pilot_program_id=payload.pilot_program_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            currency=payload.currency,
            external_reference=payload.external_reference,
            checksum_sha256=_canonical_hash(
                payload.model_dump(mode="json")
            ),
            status="draft",
            rows_count=len(payload.lines),
            gross_minor=sum(x.gross_amount_minor for x in payload.lines),
            fees_minor=sum(x.fee_minor for x in payload.lines),
            refunds_minor=sum(x.refund_minor for x in payload.lines),
            net_settlement_minor=sum(
                x.net_settlement_minor for x in payload.lines
            ),
            created_by_admin_id=admin_id,
        )
        self.db.add(batch)
        self.db.flush()
        seen: set[str] = set()
        for item in payload.lines:
            if item.provider_transaction_id in seen:
                raise ApiError(
                    409,
                    "settlement_duplicate_transaction",
                    "معاملة مكررة داخل ملف التسوية.",
                )
            seen.add(item.provider_transaction_id)
            self.db.add(
                ProviderSettlementLineEntity(
                    batch_id=batch.id,
                    provider_transaction_id=item.provider_transaction_id,
                    settlement_reference=item.settlement_reference,
                    gross_amount_minor=item.gross_amount_minor,
                    fee_minor=item.fee_minor,
                    refund_minor=item.refund_minor,
                    net_settlement_minor=item.net_settlement_minor,
                    currency=payload.currency,
                    is_settled=item.is_settled,
                    settled_at=item.settled_at,
                    raw_json=item.raw_json,
                )
            )
        self.audit.add(
            action="finance.settlement.created",
            actor_user_id=admin_id,
            entity_type="provider_settlement_batch",
            entity_id=str(batch.id),
            request_id=request_id,
            metadata={
                "provider": batch.provider,
                "rows": batch.rows_count,
                "gross_minor": batch.gross_minor,
                "fees_minor": batch.fees_minor,
            },
        )
        self.db.commit()
        return self.settlement_detail(batch.id)

    def reconcile_settlement(
        self,
        *,
        batch_id: UUID,
        admin_id: UUID | None,
        request_id: str | None,
    ) -> SettlementBatchDetail:
        batch = self.db.get(ProviderSettlementBatchEntity, batch_id)
        if batch is None:
            raise ApiError(404, "settlement_not_found", "دفعة التسوية غير موجودة.")
        if batch.status == "reconciled":
            return self.settlement_detail(batch.id)

        program = self._program(batch.pilot_program_id)
        program_orders: set[UUID] | None = None
        if program is not None:
            start, end = self.economics._period(program)
            program_orders = {
                x.id for x in self.economics._orders(program, start, end)
            }

        lines = list(
            self.db.scalars(
                select(ProviderSettlementLineEntity).where(
                    ProviderSettlementLineEntity.batch_id == batch.id
                )
            ).all()
        )

        all_clean = True
        matched = 0
        mismatched = 0
        blockers: list[str] = []

        # First pass: validate every line. No fee cost is created unless the
        # whole settlement batch reconciles cleanly.
        for line in lines:
            issues: list[str] = []
            tx = self.db.scalar(
                select(PaymentProviderTransactionEntity).where(
                    PaymentProviderTransactionEntity.provider
                    == batch.provider,
                    PaymentProviderTransactionEntity.provider_transaction_id
                    == line.provider_transaction_id,
                )
            )
            if tx is None:
                line.reconciliation_status = "unmatched"
                line.issues_json = ["provider_transaction_not_found"]
                all_clean = False
                mismatched += 1
                continue

            payment = (
                self.db.get(PaymentEntity, tx.payment_id)
                if tx.payment_id
                else None
            )
            if payment is None:
                issues.append("matched_payment_not_found")
            else:
                line.matched_payment_id = payment.id
                if (
                    program_orders is not None
                    and payment.order_id not in program_orders
                ):
                    issues.append("payment_outside_pilot_program")

            if tx.transaction_type != "payment":
                issues.append("settlement_line_not_payment_transaction")
            if not tx.success or tx.pending:
                issues.append("provider_transaction_not_successful")
            if tx.currency.upper() != line.currency.upper():
                issues.append("currency_mismatch")
            if tx.amount_minor != line.gross_amount_minor:
                issues.append("gross_amount_mismatch")
            if line.refund_minor > line.gross_amount_minor:
                issues.append("refund_exceeds_gross")
            expected_net = max(
                0,
                line.gross_amount_minor
                - line.refund_minor
                - line.fee_minor,
            )
            if expected_net != line.net_settlement_minor:
                issues.append("net_settlement_formula_mismatch")
            if not line.is_settled or line.settled_at is None:
                issues.append("transaction_not_settled")
            if (
                (tx.is_refunded or tx.refunded_minor > 0)
                and tx.refunded_minor != line.refund_minor
            ):
                issues.append("provider_refund_snapshot_mismatch")

            # Avoid double-counting a payment-processing cost that was already
            # verified from another source.
            if payment is not None and line.fee_minor > 0:
                existing_processing = self.db.scalar(
                    select(EconomicsCostEntryEntity).where(
                        EconomicsCostEntryEntity.order_id
                        == payment.order_id,
                        EconomicsCostEntryEntity.cost_type
                        == "payment_processing",
                        EconomicsCostEntryEntity.is_verified.is_(True),
                        EconomicsCostEntryEntity.external_reference
                        != (
                            f"settlement:{batch.external_reference}:"
                            f"{line.provider_transaction_id}:fee"
                        ),
                    )
                )
                if existing_processing is not None:
                    issues.append(
                        "payment_processing_cost_already_exists"
                    )

            if issues:
                line.reconciliation_status = "mismatch"
                line.issues_json = issues
                all_clean = False
                mismatched += 1
            else:
                line.reconciliation_status = "matched"
                line.issues_json = []
                matched += 1

        if not all_clean:
            batch.status = "blocked"
            batch.operations_status = "open"
            blockers = sorted(
                {
                    issue
                    for line in lines
                    for issue in line.issues_json
                }
            )
            batch.blockers_json = blockers
            batch.matched_lines = matched
            batch.mismatched_lines = mismatched
            batch.reconciled_by_admin_id = admin_id
            batch.reconciled_at = utc_now()
            self.audit.add(
                action="finance.settlement.blocked",
                actor_user_id=admin_id,
                entity_type="provider_settlement_batch",
                entity_id=str(batch.id),
                request_id=request_id,
                metadata={
                    "matched": matched,
                    "mismatched": mismatched,
                    "blockers": blockers,
                },
            )
            self.db.commit()
            return self.settlement_detail(batch.id)

        # Second pass: materialize provider fees as verified operational costs.
        for line in lines:
            if line.fee_minor <= 0 or line.applied_cost_entry_id is not None:
                continue
            payment = self.db.get(PaymentEntity, line.matched_payment_id)
            if payment is None:
                continue
            ext_ref = (
                f"settlement:{batch.external_reference}:"
                f"{line.provider_transaction_id}:fee"
            )
            existing = self.db.scalar(
                select(EconomicsCostEntryEntity).where(
                    EconomicsCostEntryEntity.source == "provider",
                    EconomicsCostEntryEntity.external_reference == ext_ref,
                )
            )
            if existing is None:
                order = self.db.get(OrderEntity, payment.order_id)
                cost = EconomicsCostEntryEntity(
                    pilot_program_id=batch.pilot_program_id,
                    order_id=payment.order_id,
                    area=program.area if program else None,
                    incurred_on=(
                        line.settled_at.date()
                        if line.settled_at
                        else (
                            order.service_date
                            if order is not None
                            else batch.period_end
                        )
                    ),
                    cost_type="payment_processing",
                    cost_scope="variable",
                    amount_minor=line.fee_minor,
                    currency="EGP",
                    source="provider",
                    external_reference=ext_ref,
                    note="Paymob settled provider fee",
                    is_verified=True,
                    verified_by_admin_id=admin_id,
                    verified_at=utc_now(),
                    created_by_admin_id=admin_id,
                )
                self.db.add(cost)
                self.db.flush()
                existing = cost
            line.applied_cost_entry_id = existing.id

        batch.status = "reconciled"
        batch.operations_status = "review"
        batch.blockers_json = []
        batch.matched_lines = len(lines)
        batch.mismatched_lines = 0
        batch.reconciled_by_admin_id = admin_id
        batch.reconciled_at = utc_now()
        self.audit.add(
            action="finance.settlement.reconciled",
            actor_user_id=admin_id,
            entity_type="provider_settlement_batch",
            entity_id=str(batch.id),
            request_id=request_id,
            metadata={
                "rows": len(lines),
                "fees_minor": batch.fees_minor,
                "net_settlement_minor": batch.net_settlement_minor,
            },
        )
        self.db.commit()
        return self.settlement_detail(batch.id)

    def reconcile_pending_settlements(
        self,
        *,
        limit: int = 50,
    ) -> dict:
        rows = list(
            self.db.scalars(
                select(ProviderSettlementBatchEntity)
                .where(
                    ProviderSettlementBatchEntity.status.in_(
                        ["draft", "blocked"]
                    )
                )
                .order_by(
                    ProviderSettlementBatchEntity.created_at.asc()
                )
                .limit(limit)
            ).all()
        )
        reconciled = 0
        blocked = 0
        for row in rows:
            result = self.reconcile_settlement(
                batch_id=row.id,
                admin_id=None,
                request_id=None,
            )
            if result.batch.status == "reconciled":
                reconciled += 1
            else:
                blocked += 1
        return {
            "scanned": len(rows),
            "reconciled": reconciled,
            "blocked": blocked,
        }

    def settlement_detail(self, batch_id: UUID) -> SettlementBatchDetail:
        batch = self.db.get(ProviderSettlementBatchEntity, batch_id)
        if batch is None:
            raise ApiError(404, "settlement_not_found", "دفعة التسوية غير موجودة.")
        lines = list(
            self.db.scalars(
                select(ProviderSettlementLineEntity)
                .where(ProviderSettlementLineEntity.batch_id == batch.id)
                .order_by(ProviderSettlementLineEntity.created_at.asc())
            ).all()
        )
        return SettlementBatchDetail(
            batch=SettlementBatchResponse.model_validate(batch),
            lines=[
                SettlementLineResponse.model_validate(x)
                for x in lines
            ],
        )

    def settlements(
        self,
        *,
        status: str | None,
        limit: int,
    ) -> list[SettlementBatchResponse]:
        stmt = select(ProviderSettlementBatchEntity)
        if status:
            stmt = stmt.where(
                ProviderSettlementBatchEntity.status == status
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(
                    ProviderSettlementBatchEntity.created_at.desc()
                ).limit(limit)
            ).all()
        )
        return [
            SettlementBatchResponse.model_validate(x)
            for x in rows
        ]

    # ------------------------------------------------------------------
    # Expansion zone budget controls
    # ------------------------------------------------------------------
    def required_budget_categories(self) -> list[str]:
        return [
            x.strip()
            for x in self.settings.expansion_required_budget_categories.split(",")
            if x.strip()
        ]

    def _budget_response(
        self,
        row: ExpansionZoneBudgetEntity,
    ) -> ZoneBudgetResponse:
        response = ZoneBudgetResponse.model_validate(row)
        response.remaining_minor = (
            row.allocated_minor
            - row.committed_minor
            - row.spent_minor
        )
        return response

    def upsert_budget(
        self,
        *,
        zone_id: UUID,
        payload: ZoneBudgetUpsert,
        admin_id: UUID,
        request_id: str | None,
    ) -> ZoneBudgetResponse:
        self._zone(zone_id)
        row = self.db.scalar(
            select(ExpansionZoneBudgetEntity).where(
                ExpansionZoneBudgetEntity.zone_id == zone_id,
                ExpansionZoneBudgetEntity.category == payload.category,
            )
        )
        if row is None:
            row = ExpansionZoneBudgetEntity(
                zone_id=zone_id,
                category=payload.category,
                allocated_minor=payload.allocated_minor,
                currency="EGP",
                note=payload.note,
                created_by_admin_id=admin_id,
                updated_by_admin_id=admin_id,
            )
            self.db.add(row)
        else:
            if (
                payload.allocated_minor
                < row.committed_minor + row.spent_minor
            ):
                raise ApiError(
                    409,
                    "expansion_budget_below_used_amount",
                    "لا يمكن خفض الميزانية تحت المبلغ المستخدم/الملتزم.",
                )
            row.allocated_minor = payload.allocated_minor
            row.note = payload.note
            row.updated_by_admin_id = admin_id
        self.db.flush()
        self.audit.add(
            action="expansion.budget.upserted",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone_id),
            request_id=request_id,
            metadata={
                "category": row.category,
                "allocated_minor": row.allocated_minor,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return self._budget_response(row)

    def move_budget(
        self,
        *,
        budget_id: UUID,
        payload: ZoneBudgetMovement,
        admin_id: UUID,
        request_id: str | None,
    ) -> ZoneBudgetResponse:
        row = self.db.get(ExpansionZoneBudgetEntity, budget_id)
        if row is None:
            raise ApiError(
                404,
                "expansion_budget_not_found",
                "ميزانية المنطقة غير موجودة.",
            )
        amount = payload.amount_minor
        if payload.action == "commit":
            if (
                row.committed_minor
                + row.spent_minor
                + amount
                > row.allocated_minor
            ):
                raise ApiError(
                    409,
                    "expansion_budget_exceeded",
                    "الالتزام الجديد يتجاوز الميزانية.",
                )
            row.committed_minor += amount
        elif payload.action == "release":
            if amount > row.committed_minor:
                raise ApiError(
                    409,
                    "expansion_budget_release_exceeds_commitment",
                    "لا يمكن تحرير أكثر من المبلغ الملتزم.",
                )
            row.committed_minor -= amount
        else:  # spend
            if row.spent_minor + amount > row.allocated_minor:
                raise ApiError(
                    409,
                    "expansion_budget_exceeded",
                    "المصروف الجديد يتجاوز الميزانية.",
                )
            from_commit = min(row.committed_minor, amount)
            row.committed_minor -= from_commit
            row.spent_minor += amount

        row.updated_by_admin_id = admin_id
        self.audit.add(
            action=f"expansion.budget.{payload.action}",
            actor_user_id=admin_id,
            entity_type="expansion_zone_budget",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "amount_minor": amount,
                "note": payload.note,
                "zone_id": str(row.zone_id),
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return self._budget_response(row)

    def budget_summary(self, zone_id: UUID) -> ZoneBudgetSummary:
        self._zone(zone_id)
        rows = list(
            self.db.scalars(
                select(ExpansionZoneBudgetEntity)
                .where(ExpansionZoneBudgetEntity.zone_id == zone_id)
                .order_by(ExpansionZoneBudgetEntity.category.asc())
            ).all()
        )
        required = self.required_budget_categories()
        present = [x.category for x in rows if x.allocated_minor > 0]
        missing = [x for x in required if x not in present]
        allocated = sum(x.allocated_minor for x in rows)
        committed = sum(x.committed_minor for x in rows)
        spent = sum(x.spent_minor for x in rows)
        remaining = allocated - committed - spent
        return ZoneBudgetSummary(
            zone_id=zone_id,
            required_categories=required,
            present_categories=present,
            missing_categories=missing,
            allocated_minor=allocated,
            committed_minor=committed,
            spent_minor=spent,
            remaining_minor=remaining,
            budget_ready=(not missing and allocated > 0 and remaining >= 0),
            budgets=[self._budget_response(x) for x in rows],
        )

    # ------------------------------------------------------------------
    # Controlled expansion rollout
    # ------------------------------------------------------------------
    def _financial_rollout_blockers(
        self,
        zone: ExpansionZoneEntity,
    ) -> tuple[list[str], ZoneBudgetSummary, int, int]:
        budget = self.budget_summary(zone.id)
        blockers: list[str] = []
        if not budget.budget_ready:
            blockers.extend(
                f"budget_missing_{x}"
                for x in budget.missing_categories
            )
            if budget.allocated_minor <= 0:
                blockers.append("launch_budget_not_allocated")

        open_reconciliation = int(
            self.db.scalar(
                select(func.count(PaymentReconciliationIssueEntity.id)).where(
                    PaymentReconciliationIssueEntity.status == "open"
                )
            )
            or 0
        )
        if open_reconciliation:
            blockers.append("payment_reconciliation_open")

        blocked_settlements = int(
            self.db.scalar(
                select(func.count(ProviderSettlementBatchEntity.id)).where(
                    ProviderSettlementBatchEntity.pilot_program_id
                    == zone.source_program_id,
                    ProviderSettlementBatchEntity.status == "blocked",
                )
            )
            or 0
        )
        if blocked_settlements:
            blockers.append("blocked_provider_settlement_batches")

        if self.settings.vendor_accounting_require_closed_settlements_for_rollout:
            unclosed_settlements = int(
                self.db.scalar(
                    select(func.count(ProviderSettlementBatchEntity.id)).where(
                        ProviderSettlementBatchEntity.pilot_program_id
                        == zone.source_program_id,
                        ProviderSettlementBatchEntity.operations_status
                        != "closed",
                    )
                )
                or 0
            )
            if unclosed_settlements:
                blockers.append("unclosed_provider_settlement_batches")

        return (
            blockers,
            budget,
            open_reconciliation,
            blocked_settlements,
        )

    def _record_rollout(
        self,
        *,
        zone: ExpansionZoneEntity,
        from_stage: str,
        to_stage: str,
        assessment_id: UUID | None,
        budget: ZoneBudgetSummary,
        admin_id: UUID | None,
        trigger_source: str = "admin",
        trigger_reason: str | None = None,
        trigger_evidence: dict | None = None,
    ) -> ExpansionRolloutEventEntity:
        row = ExpansionRolloutEventEntity(
            zone_id=zone.id,
            from_stage=from_stage,
            to_stage=to_stage,
            rollout_percent=zone.rollout_percent,
            daily_order_cap=zone.daily_order_cap,
            assessment_id=assessment_id,
            budget_snapshot_json=budget.model_dump(mode="json"),
            triggered_by_admin_id=admin_id,
            trigger_source=trigger_source,
            trigger_reason=trigger_reason,
            trigger_evidence_json=trigger_evidence or {},
        )
        self.db.add(row)
        self.db.flush()
        return row

    def rollout_history(
        self,
        *,
        zone_id: UUID,
        limit: int = 100,
    ) -> list[RolloutEventResponse]:
        self._zone(zone_id)
        rows = list(
            self.db.scalars(
                select(ExpansionRolloutEventEntity)
                .where(ExpansionRolloutEventEntity.zone_id == zone_id)
                .order_by(ExpansionRolloutEventEntity.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [
            RolloutEventResponse.model_validate(x)
            for x in rows
        ]

    def _require_launch_command_session(
        self,
        zone_id: UUID,
    ) -> None:
        if not self.settings.launch_command_required:
            return
        session = self.db.scalar(
            select(LaunchCommandSessionEntity).where(
                LaunchCommandSessionEntity.zone_id == zone_id,
                LaunchCommandSessionEntity.status == "active",
            )
        )
        if session is None:
            raise ApiError(
                409,
                "launch_command_session_required",
                "Pilot/Production rollout requires an active Launch Command Session.",
            )

    def start_rollout(
        self,
        *,
        zone_id: UUID,
        payload: RolloutRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> RolloutResponse:
        self._require_launch_command_session(zone_id)
        zone = self._zone(zone_id)
        if zone.status != "approved":
            raise ApiError(
                409,
                "expansion_zone_not_approved",
                "المنطقة يجب أن تكون معتمدة قبل بدء rollout.",
            )
        assessment = self.economics.assess_zone(
            zone_id=zone.id,
            admin_id=admin_id,
            request_id=request_id,
        )
        blockers, budget, open_rec, blocked_settlements = (
            self._financial_rollout_blockers(zone)
        )
        if assessment.decision != "ready":
            blockers.append("expansion_readiness_not_ready")
        blockers = list(dict.fromkeys(blockers))
        if blockers:
            raise ApiError(
                409,
                "expansion_rollout_blocked",
                "لا يمكن بدء rollout قبل إغلاق بوابات المال والجاهزية.",
                details={"blockers": blockers},
            )

        previous = zone.rollout_stage
        zone.status = "live"
        zone.rollout_stage = "canary"
        zone.rollout_percent = self.settings.expansion_canary_percent
        zone.daily_order_cap = (
            payload.daily_order_cap
            or self.settings.expansion_default_daily_order_cap
        )
        zone.rollout_started_at = utc_now()
        zone.rollout_completed_at = None
        zone.paused_at = None
        event = self._record_rollout(
            zone=zone,
            from_stage=previous,
            to_stage="canary",
            assessment_id=assessment.id,
            budget=budget,
            admin_id=admin_id,
        )
        self.audit.add(
            action="expansion.rollout.started",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={
                "percent": zone.rollout_percent,
                "daily_order_cap": zone.daily_order_cap,
                "assessment_id": str(assessment.id),
            },
        )
        self.db.commit()
        return RolloutResponse(
            zone_id=zone.id,
            zone_status=zone.status,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            daily_order_cap=zone.daily_order_cap,
            assessment_id=assessment.id,
            budget_ready=budget.budget_ready,
            payment_reconciliation_open=open_rec,
            blocked_settlement_batches=blocked_settlements,
            blockers=[],
            event_id=event.id,
        )

    def advance_rollout(
        self,
        *,
        zone_id: UUID,
        payload: RolloutRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> RolloutResponse:
        self._require_launch_command_session(zone_id)
        zone = self._zone(zone_id)
        if zone.status != "live" or zone.rollout_stage not in {
            "canary",
            "limited",
        }:
            raise ApiError(
                409,
                "expansion_rollout_not_advanceable",
                "المنطقة ليست في مرحلة rollout قابلة للتقدم.",
            )

        assessment = self.economics.assess_zone(
            zone_id=zone.id,
            admin_id=admin_id,
            request_id=request_id,
        )
        blockers, budget, open_rec, blocked_settlements = (
            self._financial_rollout_blockers(zone)
        )
        if assessment.decision != "ready":
            blockers.append("expansion_readiness_not_ready")
        blockers = list(dict.fromkeys(blockers))
        if blockers:
            raise ApiError(
                409,
                "expansion_rollout_blocked",
                "لا يمكن توسيع rollout قبل إغلاق البوابات.",
                details={"blockers": blockers},
            )

        previous = zone.rollout_stage
        if previous == "canary":
            zone.rollout_stage = "limited"
            zone.rollout_percent = self.settings.expansion_limited_percent
            zone.daily_order_cap = (
                payload.daily_order_cap
                or max(
                    self.settings.expansion_default_daily_order_cap * 4,
                    zone.daily_order_cap or 0,
                )
            )
        else:
            zone.rollout_stage = "full"
            zone.rollout_percent = 100
            zone.daily_order_cap = payload.daily_order_cap
            zone.rollout_completed_at = utc_now()

        event = self._record_rollout(
            zone=zone,
            from_stage=previous,
            to_stage=zone.rollout_stage,
            assessment_id=assessment.id,
            budget=budget,
            admin_id=admin_id,
        )
        self.audit.add(
            action="expansion.rollout.advanced",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={
                "from": previous,
                "to": zone.rollout_stage,
                "percent": zone.rollout_percent,
            },
        )
        self.db.commit()
        return RolloutResponse(
            zone_id=zone.id,
            zone_status=zone.status,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            daily_order_cap=zone.daily_order_cap,
            assessment_id=assessment.id,
            budget_ready=budget.budget_ready,
            payment_reconciliation_open=open_rec,
            blocked_settlement_batches=blocked_settlements,
            blockers=[],
            event_id=event.id,
        )

    def pause_rollout(
        self,
        *,
        zone_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> RolloutResponse:
        zone = self._zone(zone_id)
        if zone.status != "live" or zone.rollout_stage not in {
            "canary",
            "limited",
            "full",
        }:
            raise ApiError(
                409,
                "expansion_rollout_not_live",
                "لا يوجد rollout نشط لإيقافه.",
            )
        budget = self.budget_summary(zone.id)
        previous = zone.rollout_stage
        zone.status = "paused"
        zone.rollout_stage = "paused"
        zone.paused_at = utc_now()
        event = self._record_rollout(
            zone=zone,
            from_stage=previous,
            to_stage="paused",
            assessment_id=None,
            budget=budget,
            admin_id=admin_id,
        )
        self.audit.add(
            action="expansion.rollout.paused",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={"from": previous},
        )
        self.db.commit()
        return RolloutResponse(
            zone_id=zone.id,
            zone_status=zone.status,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            daily_order_cap=zone.daily_order_cap,
            assessment_id=None,
            budget_ready=budget.budget_ready,
            payment_reconciliation_open=0,
            blocked_settlement_batches=0,
            blockers=[],
            event_id=event.id,
        )

    def auto_pause_rollout(
        self,
        *,
        zone_id: UUID,
        monitoring_snapshot_id: UUID,
        blockers: list[str],
        red_streak: int,
        required_red_streak: int,
    ) -> RolloutResponse | None:
        """Pause an active rollout from durable SLO evidence.

        This deliberately reuses the same rollout state/event model as manual
        Pause, but records a system trigger and never auto-resumes. Repeated
        evaluation is idempotent because only an active rollout is transitionable.
        """
        zone = self._zone(zone_id)
        if zone.status != "live" or zone.rollout_stage not in {
            "canary",
            "limited",
            "full",
        }:
            return None

        budget = self.budget_summary(zone.id)
        previous = zone.rollout_stage
        evidence = {
            "monitoring_snapshot_id": str(monitoring_snapshot_id),
            "blockers": list(blockers),
            "red_streak": red_streak,
            "required_red_streak": required_red_streak,
            "previous_rollout_stage": previous,
            "previous_rollout_percent": zone.rollout_percent,
        }
        zone.status = "paused"
        zone.rollout_stage = "paused"
        zone.paused_at = utc_now()
        event = self._record_rollout(
            zone=zone,
            from_stage=previous,
            to_stage="paused",
            assessment_id=None,
            budget=budget,
            admin_id=None,
            trigger_source="system",
            trigger_reason="slo_auto_pause",
            trigger_evidence=evidence,
        )

        command_session = self.db.scalar(
            select(LaunchCommandSessionEntity)
            .where(
                LaunchCommandSessionEntity.zone_id == zone.id,
                LaunchCommandSessionEntity.status.in_(["active", "paused"]),
            )
            .order_by(LaunchCommandSessionEntity.created_at.desc())
            .limit(1)
        )
        if command_session is not None:
            self.db.add(
                LaunchCommandEventEntity(
                    session_id=command_session.id,
                    event_type="slo.auto_pause",
                    severity="critical",
                    title="Rollout auto-paused by SLO policy",
                    details_json={**evidence, "rollout_event_id": str(event.id)},
                    actor_admin_id=None,
                )
            )

        self.audit.add(
            action="expansion.rollout.auto_paused",
            actor_user_id=None,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            metadata={**evidence, "rollout_event_id": str(event.id)},
        )
        self.db.commit()
        return RolloutResponse(
            zone_id=zone.id,
            zone_status=zone.status,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            daily_order_cap=zone.daily_order_cap,
            assessment_id=None,
            budget_ready=budget.budget_ready,
            payment_reconciliation_open=0,
            blocked_settlement_batches=0,
            blockers=list(blockers),
            event_id=event.id,
        )

    def resume_rollout(
        self,
        *,
        zone_id: UUID,
        admin_id: UUID,
        request_id: str | None,
    ) -> RolloutResponse:
        self._require_launch_command_session(zone_id)
        zone = self._zone(zone_id)
        if zone.status != "paused" or zone.rollout_stage != "paused":
            raise ApiError(
                409,
                "expansion_rollout_not_paused",
                "المنطقة ليست في حالة rollout متوقف.",
            )
        pause_event = self.db.scalar(
            select(ExpansionRolloutEventEntity)
            .where(
                ExpansionRolloutEventEntity.zone_id == zone.id,
                ExpansionRolloutEventEntity.to_stage == "paused",
            )
            .order_by(ExpansionRolloutEventEntity.created_at.desc())
        )
        resume_stage = (
            pause_event.from_stage
            if pause_event is not None
            else "canary"
        )
        assessment = self.economics.assess_zone(
            zone_id=zone.id,
            admin_id=admin_id,
            request_id=request_id,
        )
        blockers, budget, open_rec, blocked_settlements = (
            self._financial_rollout_blockers(zone)
        )
        if assessment.decision != "ready":
            blockers.append("expansion_readiness_not_ready")
        if blockers:
            raise ApiError(
                409,
                "expansion_rollout_blocked",
                "لا يمكن استئناف rollout قبل إغلاق البوابات.",
                details={"blockers": list(dict.fromkeys(blockers))},
            )
        previous = zone.rollout_stage
        zone.status = "live"
        zone.rollout_stage = resume_stage
        zone.paused_at = None
        event = self._record_rollout(
            zone=zone,
            from_stage=previous,
            to_stage=resume_stage,
            assessment_id=assessment.id,
            budget=budget,
            admin_id=admin_id,
        )
        self.audit.add(
            action="expansion.rollout.resumed",
            actor_user_id=admin_id,
            entity_type="expansion_zone",
            entity_id=str(zone.id),
            request_id=request_id,
            metadata={"to": resume_stage},
        )
        self.db.commit()
        return RolloutResponse(
            zone_id=zone.id,
            zone_status=zone.status,
            rollout_stage=zone.rollout_stage,
            rollout_percent=zone.rollout_percent,
            daily_order_cap=zone.daily_order_cap,
            assessment_id=assessment.id,
            budget_ready=budget.budget_ready,
            payment_reconciliation_open=open_rec,
            blocked_settlement_batches=blocked_settlements,
            blockers=[],
            event_id=event.id,
        )
