from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    AuthSessionEntity,
    BackgroundJobEntity,
    OtpChallengeEntity,
    PaymentEntity,
)
from app.core.security import utc_now
from app.modules.orders.service import OrderService
from app.modules.special_orders.service import SpecialOrderService
from app.modules.security_hardening.service import SecurityService
from app.modules.notification_delivery.service import NotificationDeliveryService
from app.modules.payment_reconciliation.service import PaymentReconciliationService
from app.modules.operations_control.service import OperationsControlService
from app.modules.pilot_stability.service import PilotStabilityService
from app.modules.financial_automation.service import FinancialAutomationService
from app.modules.launch_governance.service import LaunchTrafficGovernanceService
from app.modules.launch_command.service import LaunchCommandService


class BackgroundJobService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def enqueue(
        self,
        *,
        job_type: str,
        idempotency_key: str,
        payload: dict | None = None,
        available_at=None,
        max_attempts: int | None = None,
    ) -> BackgroundJobEntity:
        existing = self.db.scalar(
            select(BackgroundJobEntity).where(
                BackgroundJobEntity.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            return existing
        row = BackgroundJobEntity(
            job_type=job_type,
            payload_json=payload or {},
            idempotency_key=idempotency_key,
            status="queued",
            attempts=0,
            max_attempts=max_attempts or self.settings.background_job_max_attempts,
            available_at=available_at or utc_now(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def schedule_maintenance(self) -> list[BackgroundJobEntity]:
        now = utc_now()
        bucket = now.strftime("%Y%m%d%H%M")
        jobs = [
            ("maintenance.release_expired_holds", {}),
            ("maintenance.expire_special_orders", {}),
            ("maintenance.expire_pending_payments", {}),
            ("maintenance.cleanup_auth", {}),
            ("maintenance.cleanup_security", {}),
            ("notifications.dispatch", {}),
            ("notifications.reconcile", {}),
            ("payments.reconcile", {}),
            ("finance.settlements.reconcile", {}),
            ("expansion.monitor", {}),
            ("launch.command.maintain", {}),
            ("operations.scan", {}),
        ]
        rows = []
        for job_type, payload in jobs:
            rows.append(
                self.enqueue(
                    job_type=job_type,
                    idempotency_key=f"{job_type}:{bucket}",
                    payload=payload,
                )
            )
        daily_bucket = now.strftime("%Y%m%d")
        rows.append(
            self.enqueue(
                job_type="pilot.snapshot",
                idempotency_key=f"pilot.snapshot:{daily_bucket}",
                payload={},
            )
        )
        self.db.commit()
        return rows

    def recover_stale(self) -> int:
        cutoff = utc_now() - timedelta(seconds=self.settings.worker_stale_seconds)
        rows = list(
            self.db.scalars(
                select(BackgroundJobEntity).where(
                    BackgroundJobEntity.status == "running",
                    BackgroundJobEntity.locked_at.is_not(None),
                    BackgroundJobEntity.locked_at <= cutoff,
                )
            ).all()
        )
        for row in rows:
            row.status = "retry"
            row.locked_at = None
            row.locked_by = None
            row.last_error = "stale_running_lock_recovered"
            row.available_at = utc_now()
        if rows:
            self.db.commit()
        return len(rows)

    def claim_one(self, *, worker_id: str) -> BackgroundJobEntity | None:
        now = utc_now()
        stmt = (
            select(BackgroundJobEntity)
            .where(
                BackgroundJobEntity.status.in_(["queued", "retry"]),
                BackgroundJobEntity.available_at <= now,
            )
            .order_by(BackgroundJobEntity.created_at.asc())
            .limit(1)
        )
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        row = self.db.scalar(stmt)
        if row is None:
            return None
        row.status = "running"
        row.attempts += 1
        row.locked_at = now
        row.locked_by = worker_id
        self.db.commit()
        return row

    def execute(self, job: BackgroundJobEntity) -> dict:
        if job.job_type == "maintenance.release_expired_holds":
            released = OrderService(self.db, self.settings).release_expired_holds()
            return {"released_reservations": released}
        if job.job_type == "maintenance.expire_special_orders":
            expired = SpecialOrderService(self.db, self.settings).expire_due_requests()
            return {"expired_special_orders": expired}
        if job.job_type == "maintenance.expire_pending_payments":
            return self._expire_pending_payments()
        if job.job_type == "maintenance.cleanup_auth":
            return self._cleanup_auth()
        if job.job_type == "maintenance.cleanup_security":
            return SecurityService(self.db, self.settings).cleanup()
        if job.job_type == "notifications.dispatch":
            service = NotificationDeliveryService(self.db, self.settings)
            recovered = service.recover_stale()
            result = service.dispatch_due(worker_id=job.locked_by or "notification-worker", limit=self.settings.notification_dispatch_batch_size)
            return {"recovered": recovered, **result}
        if job.job_type == "notifications.reconcile":
            return NotificationDeliveryService(self.db, self.settings).reconcile()
        if job.job_type == "payments.reconcile":
            result = PaymentReconciliationService(
                self.db,
                self.settings,
            ).run()
            return result.model_dump(mode="json")
        if job.job_type == "finance.settlements.reconcile":
            return FinancialAutomationService(
                self.db,
                self.settings,
            ).reconcile_pending_settlements()
        if job.job_type == "expansion.monitor":
            return LaunchTrafficGovernanceService(
                self.db,
                self.settings,
            ).refresh_all_live_zones()
        if job.job_type == "launch.command.maintain":
            return LaunchCommandService(
                self.db,
                self.settings,
            ).maintain()
        if job.job_type == "operations.scan":
            return OperationsControlService(
                self.db,
                self.settings,
            ).refresh_incidents().model_dump(mode="json")
        if job.job_type == "pilot.snapshot":
            return PilotStabilityService(
                self.db,
                self.settings,
            ).refresh_active_programs()
        raise ValueError(f"Unknown background job type: {job.job_type}")

    def _expire_pending_payments(self) -> dict:
        now = utc_now()
        rows = list(
            self.db.scalars(
                select(PaymentEntity).where(
                    PaymentEntity.status == "pending",
                    PaymentEntity.expires_at <= now,
                )
            ).all()
        )
        for row in rows:
            row.status = "expired"
            row.failed_at = now
        self.db.commit()
        return {"expired_payments": len(rows)}

    def _cleanup_auth(self) -> dict:
        now = utc_now()
        otp_result = self.db.execute(
            delete(OtpChallengeEntity).where(OtpChallengeEntity.expires_at <= now)
        )
        session_result = self.db.execute(
            delete(AuthSessionEntity).where(
                or_(
                    AuthSessionEntity.expires_at <= now,
                    AuthSessionEntity.revoked_at <= now - timedelta(days=7),
                )
            )
        )
        self.db.commit()
        return {
            "deleted_otp_challenges": int(otp_result.rowcount or 0),
            "deleted_auth_sessions": int(session_result.rowcount or 0),
        }

    def mark_succeeded(self, job_id: UUID, result: dict) -> None:
        row = self.db.get(BackgroundJobEntity, job_id)
        if row is None:
            return
        row.status = "succeeded"
        row.result_json = result
        row.finished_at = utc_now()
        row.locked_at = None
        row.locked_by = None
        row.last_error = None
        self.db.commit()

    def mark_failed(self, job_id: UUID, exc: Exception) -> None:
        row = self.db.get(BackgroundJobEntity, job_id)
        if row is None:
            return
        row.last_error = str(exc)[:4000]
        row.locked_at = None
        row.locked_by = None
        if row.attempts >= row.max_attempts:
            row.status = "dead_letter"
            row.finished_at = utc_now()
        else:
            row.status = "retry"
            delay = min(
                3600,
                self.settings.retry_base_seconds * (2 ** max(0, row.attempts - 1)),
            )
            row.available_at = utc_now() + timedelta(seconds=delay)
        self.db.commit()

    def run_due(self, *, worker_id: str, limit: int) -> dict:
        succeeded = 0
        failed = 0
        for _ in range(limit):
            job = self.claim_one(worker_id=worker_id)
            if job is None:
                break
            try:
                result = self.execute(job)
                self.mark_succeeded(job.id, result)
                succeeded += 1
            except Exception as exc:
                self.db.rollback()
                self.mark_failed(job.id, exc)
                failed += 1
        return {"succeeded": succeeded, "failed": failed}

    def counts(self) -> dict[str, int]:
        rows = self.db.execute(
            select(BackgroundJobEntity.status, func.count(BackgroundJobEntity.id))
            .group_by(BackgroundJobEntity.status)
        ).all()
        result = {status: int(count) for status, count in rows}
        for key in ["queued", "running", "retry", "succeeded", "dead_letter", "cancelled"]:
            result.setdefault(key, 0)
        return result
