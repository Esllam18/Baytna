from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    NotificationDeliveryEntity,
    NotificationEntity,
    NotificationPreferenceEntity,
    NotificationProviderEventEntity,
    PushDeviceEntity,
    UserEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.notification_delivery.crypto import IntegrationSecretBox
from app.modules.notification_delivery.providers import (
    ProviderError,
    build_push_provider,
    build_sms_provider,
)
from app.modules.notification_delivery.schemas import (
    NotificationDeliveryResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    PushDeviceRegisterRequest,
    PushDeviceResponse,
)


ORDER_KINDS = {
    "order_confirmed",
    "chef_accepted",
    "order_ready",
    "driver_assigned",
    "order_picked_up",
    "order_delivered",
    "special_order_accepted",
    "special_order_counter_offer",
    "special_order_rejected",
    "special_order_scheduled",
}
SUPPORT_KINDS = {"support_reply", "support_status"}
SMS_ELIGIBLE_KINDS = {
    "order_delivered",
    "special_order_accepted",
    "special_order_rejected",
    "support_reply",
    "support_status",
}


class NotificationDeliveryService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.crypto = IntegrationSecretBox(settings)
        self.audit = AuditRepository(db)

    # -------------------------------------------------------------
    # Devices / preferences
    # -------------------------------------------------------------
    def register_device(
        self,
        *,
        user_id: UUID,
        payload: PushDeviceRegisterRequest,
        request_id: str | None,
    ) -> PushDeviceResponse:
        token_hash = self.crypto.hash(payload.token)
        row = self.db.scalar(
            select(PushDeviceEntity).where(
                PushDeviceEntity.token_hash == token_hash
            )
        )
        if row is None:
            row = PushDeviceEntity(
                user_id=user_id,
                platform=payload.platform,
                token_hash=token_hash,
                token_ciphertext=self.crypto.encrypt(payload.token),
            )
            self.db.add(row)
        else:
            # Provider tokens can migrate between accounts after logout/login.
            row.user_id = user_id
            row.platform = payload.platform
            row.token_ciphertext = self.crypto.encrypt(payload.token)
            row.is_active = True

        row.device_name = payload.device_name
        row.app_version = payload.app_version
        row.last_seen_at = utc_now()

        self.audit.add(
            action="notifications.device.registered",
            actor_user_id=user_id,
            entity_type="push_device",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"platform": payload.platform},
        )
        self.db.commit()
        self.db.refresh(row)
        return PushDeviceResponse.model_validate(row)

    def list_devices(self, *, user_id: UUID) -> list[PushDeviceResponse]:
        rows = list(
            self.db.scalars(
                select(PushDeviceEntity)
                .where(PushDeviceEntity.user_id == user_id)
                .order_by(PushDeviceEntity.updated_at.desc())
            ).all()
        )
        return [PushDeviceResponse.model_validate(x) for x in rows]

    def deactivate_device(
        self,
        *,
        user_id: UUID,
        device_id: UUID,
        request_id: str | None,
    ) -> None:
        row = self.db.get(PushDeviceEntity, device_id)
        if row is None or row.user_id != user_id:
            raise ApiError(404, "push_device_not_found", "الجهاز غير موجود.")
        row.is_active = False
        self.audit.add(
            action="notifications.device.deactivated",
            actor_user_id=user_id,
            entity_type="push_device",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()

    def preferences(self, *, user_id: UUID) -> NotificationPreferenceResponse:
        row = self._preference_row(user_id=user_id)
        self.db.commit()
        return NotificationPreferenceResponse.model_validate(row)

    def update_preferences(
        self,
        *,
        user_id: UUID,
        payload: NotificationPreferenceUpdateRequest,
        request_id: str | None,
    ) -> NotificationPreferenceResponse:
        row = self._preference_row(user_id=user_id)
        for key, value in payload.model_dump().items():
            setattr(row, key, value)

        self.audit.add(
            action="notifications.preferences.updated",
            actor_user_id=user_id,
            entity_type="notification_preferences",
            entity_id=str(user_id),
            request_id=request_id,
            metadata=payload.model_dump(),
        )
        self.db.commit()
        self.db.refresh(row)
        return NotificationPreferenceResponse.model_validate(row)

    def _preference_row(self, *, user_id: UUID) -> NotificationPreferenceEntity:
        row = self.db.get(NotificationPreferenceEntity, user_id)
        if row is None:
            row = NotificationPreferenceEntity(user_id=user_id)
            self.db.add(row)
            self.db.flush()
        return row

    # -------------------------------------------------------------
    # Planning
    # -------------------------------------------------------------
    def plan_for_notification(
        self,
        notification: NotificationEntity,
    ) -> list[NotificationDeliveryEntity]:
        pref = self._preference_row(user_id=notification.user_id)

        if notification.kind in ORDER_KINDS and not pref.order_updates:
            return []
        if notification.kind in SUPPORT_KINDS and not pref.support_updates:
            return []
        if notification.kind.startswith("marketing.") and not pref.marketing_enabled:
            return []

        rows: list[NotificationDeliveryEntity] = []

        if pref.push_enabled:
            devices = list(
                self.db.scalars(
                    select(PushDeviceEntity).where(
                        PushDeviceEntity.user_id == notification.user_id,
                        PushDeviceEntity.is_active.is_(True),
                    )
                ).all()
            )
            for device in devices:
                rows.append(
                    self._ensure_delivery(
                        notification=notification,
                        channel="push",
                        target_ref=str(device.id),
                        provider=self.settings.notification_push_provider,
                    )
                )

        if pref.sms_enabled and notification.kind in SMS_ELIGIBLE_KINDS:
            rows.append(
                self._ensure_delivery(
                    notification=notification,
                    channel="sms",
                    target_ref="user_phone",
                    provider=self.settings.notification_sms_provider,
                )
            )

        return rows

    def _ensure_delivery(
        self,
        *,
        notification: NotificationEntity,
        channel: str,
        target_ref: str,
        provider: str,
    ) -> NotificationDeliveryEntity:
        existing = self.db.scalar(
            select(NotificationDeliveryEntity).where(
                NotificationDeliveryEntity.notification_id == notification.id,
                NotificationDeliveryEntity.channel == channel,
                NotificationDeliveryEntity.target_ref == target_ref,
            )
        )
        if existing is not None:
            return existing

        row = NotificationDeliveryEntity(
            notification_id=notification.id,
            user_id=notification.user_id,
            channel=channel,
            target_ref=target_ref,
            provider=provider,
            status="pending",
            attempts=0,
            max_attempts=self.settings.notification_delivery_max_attempts,
            available_at=utc_now(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    # -------------------------------------------------------------
    # Worker dispatch
    # -------------------------------------------------------------
    def recover_stale(self) -> int:
        cutoff = utc_now() - timedelta(seconds=self.settings.worker_stale_seconds)
        rows = list(
            self.db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.status == "processing",
                    NotificationDeliveryEntity.locked_at.is_not(None),
                    NotificationDeliveryEntity.locked_at <= cutoff,
                )
            ).all()
        )
        for row in rows:
            row.status = "retry"
            row.locked_at = None
            row.locked_by = None
            row.available_at = utc_now()
            row.last_error = "stale_notification_delivery_recovered"
        if rows:
            self.db.commit()
        return len(rows)

    def claim_one(self, *, worker_id: str) -> NotificationDeliveryEntity | None:
        now = utc_now()
        stmt = (
            select(NotificationDeliveryEntity)
            .where(
                NotificationDeliveryEntity.status.in_(["pending", "retry"]),
                NotificationDeliveryEntity.available_at <= now,
            )
            .order_by(NotificationDeliveryEntity.created_at.asc())
            .limit(1)
        )
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        row = self.db.scalar(stmt)
        if row is None:
            return None
        row.status = "processing"
        row.attempts += 1
        row.locked_at = now
        row.locked_by = worker_id
        self.db.commit()
        return row

    def dispatch_due(self, *, worker_id: str, limit: int) -> dict:
        succeeded = 0
        failed = 0
        skipped = 0
        for _ in range(limit):
            row = self.claim_one(worker_id=worker_id)
            if row is None:
                break
            try:
                outcome = self._dispatch(row)
                if outcome == "skipped":
                    skipped += 1
                else:
                    succeeded += 1
            except Exception as exc:
                self.db.rollback()
                self._mark_failed(row.id, exc)
                failed += 1
        return {"succeeded": succeeded, "failed": failed, "skipped": skipped}

    def _dispatch(self, row: NotificationDeliveryEntity) -> str:
        notification = self.db.get(NotificationEntity, row.notification_id)
        user = self.db.get(UserEntity, row.user_id)
        if notification is None or user is None or not user.is_active:
            self._mark_skipped(row.id, "notification_or_user_missing")
            return "skipped"

        pref = self._preference_row(user_id=user.id)
        if row.channel == "push":
            if not pref.push_enabled:
                self._mark_skipped(row.id, "push_disabled")
                return "skipped"
            device = self.db.get(PushDeviceEntity, UUID(row.target_ref))
            if device is None or not device.is_active or device.user_id != user.id:
                self._mark_skipped(row.id, "push_device_inactive")
                return "skipped"
            token = self.crypto.decrypt(device.token_ciphertext)
            provider = build_push_provider(self.settings)
            result = provider.send(
                token=token,
                title=notification.title,
                body=notification.body,
                data=notification.data_json,
            )
        elif row.channel == "sms":
            if not pref.sms_enabled:
                self._mark_skipped(row.id, "sms_disabled")
                return "skipped"
            provider = build_sms_provider(self.settings)
            result = provider.send(phone=user.phone, body=notification.body)
        else:
            raise RuntimeError(f"unsupported notification channel: {row.channel}")

        current = self.db.get(NotificationDeliveryEntity, row.id)
        current.status = "succeeded"
        current.provider_message_id = result.provider_message_id
        current.provider_status = result.provider_status
        current.provider_error_code = None
        current.provider_updated_at = utc_now()
        if result.provider_status in {"delivered", "read"}:
            current.delivered_at = utc_now()
        current.locked_at = None
        current.locked_by = None
        current.last_error = None
        self.db.commit()
        return "succeeded"

    def _mark_skipped(self, delivery_id: UUID, reason: str) -> None:
        row = self.db.get(NotificationDeliveryEntity, delivery_id)
        if row is None:
            return
        row.status = "skipped"
        row.last_error = reason
        row.locked_at = None
        row.locked_by = None
        self.db.commit()

    def _mark_failed(self, delivery_id: UUID, exc: Exception) -> None:
        row = self.db.get(NotificationDeliveryEntity, delivery_id)
        if row is None:
            return
        row.last_error = str(exc)[:4000]
        row.locked_at = None
        row.locked_by = None
        row.provider_updated_at = utc_now()

        permanent = isinstance(exc, ProviderError) and exc.permanent
        if isinstance(exc, ProviderError):
            row.provider_error_code = exc.code
            row.provider_status = "failed"
            if exc.deactivate_target and row.channel == "push":
                try:
                    device = self.db.get(PushDeviceEntity, UUID(row.target_ref))
                except Exception:
                    device = None
                if device is not None:
                    device.is_active = False

        if permanent or row.attempts >= row.max_attempts:
            row.status = "dead_letter"
        else:
            row.status = "retry"
            delay = min(
                3600,
                self.settings.retry_base_seconds * (2 ** max(0, row.attempts - 1)),
            )
            row.available_at = utc_now() + timedelta(seconds=delay)
        self.db.commit()

    def retry(
        self,
        *,
        delivery_id: UUID,
    ) -> NotificationDeliveryResponse:
        row = self.db.get(NotificationDeliveryEntity, delivery_id)
        if row is None:
            raise ApiError(
                404,
                "notification_delivery_not_found",
                "محاولة الإرسال غير موجودة.",
            )
        if row.status not in {"dead_letter", "retry"}:
            raise ApiError(
                409,
                "notification_delivery_not_retryable",
                "محاولة الإرسال ليست في حالة تسمح بإعادة المحاولة.",
            )
        row.status = "retry"
        row.attempts = 0
        row.available_at = utc_now()
        row.last_error = None
        self.db.commit()
        self.db.refresh(row)
        return NotificationDeliveryResponse.model_validate(row)

    def ingest_provider_event(self, *, channel: str, provider: str, event_id: str, provider_message_id: str, event_status: str, payload: dict, payload_hash: str) -> dict:
        existing=self.db.scalar(select(NotificationProviderEventEntity).where(NotificationProviderEventEntity.provider==provider, NotificationProviderEventEntity.provider_event_id==event_id))
        if existing is not None: return {"duplicate": True, "matched": existing.matched_delivery_id is not None}
        event=NotificationProviderEventEntity(channel=channel, provider=provider, provider_event_id=event_id, provider_message_id=provider_message_id, event_status=event_status, payload_hash=payload_hash, payload_json=payload)
        self.db.add(event); self.db.flush()
        matched=self._apply_provider_event(event)
        self.db.commit(); return {"duplicate": False, "matched": matched}

    def _apply_provider_event(self, event: NotificationProviderEventEntity) -> bool:
        delivery=self.db.scalar(select(NotificationDeliveryEntity).where(NotificationDeliveryEntity.provider_message_id==event.provider_message_id, NotificationDeliveryEntity.channel==event.channel))
        if delivery is None: return False
        event.matched_delivery_id=delivery.id; event.processed_at=utc_now()
        delivery.provider_status = event.event_status
        delivery.provider_updated_at = utc_now()
        payload = event.payload_json or {}
        error_code = payload.get("ErrorCode") or payload.get("error_code")
        if error_code:
            delivery.provider_error_code = str(error_code)
        if event.event_status in {"accepted","delivered"}:
            delivery.status="succeeded"; delivery.last_error=None
            if event.event_status == "delivered":
                delivery.delivered_at=delivery.delivered_at or utc_now()
        else:
            delivery.last_error=f"provider_{event.event_status}"
            if delivery.attempts >= delivery.max_attempts: delivery.status="dead_letter"
            else: delivery.status="retry"; delivery.available_at=utc_now()+timedelta(seconds=self.settings.retry_base_seconds)
        return True

    def reconcile(self, *, limit: int | None = None) -> dict:
        limit=limit or self.settings.notification_reconciliation_batch_size
        matched=0; still_unmatched=0
        events=list(self.db.scalars(select(NotificationProviderEventEntity).where(NotificationProviderEventEntity.processed_at.is_(None)).order_by(NotificationProviderEventEntity.created_at.asc()).limit(limit)).all())
        for event in events:
            if self._apply_provider_event(event): matched += 1
            else: still_unmatched += 1
        repaired=0
        broken=list(self.db.scalars(select(NotificationDeliveryEntity).where(NotificationDeliveryEntity.status=="succeeded", NotificationDeliveryEntity.provider_message_id.is_(None)).limit(limit)).all())
        for row in broken:
            row.status="retry"; row.available_at=utc_now(); row.last_error="reconciliation_missing_provider_message_id"; repaired += 1
        self.db.commit(); return {"matched_events": matched, "unmatched_events": still_unmatched, "repaired_deliveries": repaired}


    def provider_configuration(self) -> dict:
        push_name = self.settings.notification_push_provider.strip().lower()
        sms_name = self.settings.notification_sms_provider.strip().lower()
        return {
            "push": {
                "provider": push_name,
                "configured": (
                    push_name == "logging"
                    or push_name == "disabled"
                    or (push_name == "http" and bool(self.settings.notification_push_endpoint))
                    or (push_name == "fcm" and bool(self.settings.fcm_project_id))
                ),
                "fcm_project_id": (
                    self.settings.fcm_project_id if push_name == "fcm" else None
                ),
            },
            "sms": {
                "provider": sms_name,
                "configured": (
                    sms_name == "logging"
                    or sms_name == "disabled"
                    or (sms_name == "http" and bool(self.settings.notification_sms_endpoint))
                    or (
                        sms_name == "twilio"
                        and bool(self.settings.twilio_account_sid)
                        and bool(self.settings.twilio_auth_token)
                        and bool(
                            self.settings.twilio_from_number
                            or self.settings.twilio_messaging_service_sid
                        )
                    )
                ),
                "twilio_account_sid": (
                    self.settings.twilio_account_sid if sms_name == "twilio" else None
                ),
                "status_callback_https": (
                    self.settings.twilio_status_callback_url.startswith("https://")
                    if sms_name == "twilio"
                    else None
                ),
            },
        }

    def enqueue_test_notification(
        self,
        *,
        user_id: UUID,
        channels: set[str],
        title: str,
        body: str,
    ) -> dict:
        user = self.db.get(UserEntity, user_id)
        if user is None or not user.is_active:
            raise ApiError(404, "user_not_found", "المستخدم غير موجود.")

        notification = NotificationEntity(
            user_id=user_id,
            kind="integration.test",
            title=title,
            body=body,
            action_url=None,
            data_json={"integration_test": True},
            dedupe_key=f"integration-test:{uuid4()}",
        )
        self.db.add(notification)
        self.db.flush()

        created: list[NotificationDeliveryEntity] = []
        if "push" in channels:
            devices = list(
                self.db.scalars(
                    select(PushDeviceEntity).where(
                        PushDeviceEntity.user_id == user_id,
                        PushDeviceEntity.is_active.is_(True),
                    )
                ).all()
            )
            if not devices:
                raise ApiError(
                    409,
                    "integration_test_no_push_device",
                    "لا يوجد جهاز Push فعال للمستخدم.",
                )
            for device in devices:
                created.append(
                    self._ensure_delivery(
                        notification=notification,
                        channel="push",
                        target_ref=str(device.id),
                        provider=self.settings.notification_push_provider,
                    )
                )

        if "sms" in channels:
            created.append(
                self._ensure_delivery(
                    notification=notification,
                    channel="sms",
                    target_ref="user_phone",
                    provider=self.settings.notification_sms_provider,
                )
            )

        self.db.commit()
        return {
            "notification_id": str(notification.id),
            "delivery_ids": [str(x.id) for x in created],
        }

    def dispatch_specific(
        self,
        *,
        delivery_ids: list[UUID],
        worker_id: str,
    ) -> list[NotificationDeliveryResponse]:
        responses: list[NotificationDeliveryResponse] = []
        for delivery_id in delivery_ids:
            row = self.db.get(NotificationDeliveryEntity, delivery_id)
            if row is None:
                continue
            if row.status in {"pending", "retry"}:
                row.status = "processing"
                row.attempts += 1
                row.locked_at = utc_now()
                row.locked_by = worker_id
                self.db.commit()
                try:
                    self._dispatch(row)
                except Exception as exc:
                    self.db.rollback()
                    self._mark_failed(delivery_id, exc)
            current = self.db.get(NotificationDeliveryEntity, delivery_id)
            if current is not None:
                responses.append(
                    NotificationDeliveryResponse.model_validate(current)
                )
        return responses

    def list_deliveries(
        self,
        *,
        status: str | None,
        channel: str | None,
        limit: int,
    ) -> list[NotificationDeliveryResponse]:
        stmt = select(NotificationDeliveryEntity)
        if status:
            stmt = stmt.where(NotificationDeliveryEntity.status == status)
        if channel:
            stmt = stmt.where(NotificationDeliveryEntity.channel == channel)
        stmt = stmt.order_by(NotificationDeliveryEntity.created_at.desc()).limit(limit)
        return [
            NotificationDeliveryResponse.model_validate(x)
            for x in self.db.scalars(stmt).all()
        ]
