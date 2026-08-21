from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import NotificationEntity
from app.core.errors import ApiError
from app.core.security import utc_now
from app.modules.notifications.schemas import (
    NotificationResponse,
    NotificationSummaryResponse,
)


class NotificationService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings

    def emit(
        self,
        *,
        user_id: UUID,
        kind: str,
        title: str,
        body: str,
        dedupe_key: str | None = None,
        action_url: str | None = None,
        data_json: dict | None = None,
        commit: bool = False,
    ) -> NotificationEntity:
        if dedupe_key:
            existing = self.db.scalar(
                select(NotificationEntity).where(
                    NotificationEntity.user_id == user_id,
                    NotificationEntity.dedupe_key == dedupe_key,
                )
            )
            if existing is not None:
                return existing

        from app.modules.notification_templates.service import NotificationTemplateService
        title, body = NotificationTemplateService(self.db).render(kind=kind, fallback_title=title, fallback_body=body, data=data_json or {})
        row = NotificationEntity(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            action_url=action_url,
            data_json=data_json or {},
            dedupe_key=dedupe_key,
        )
        self.db.add(row)
        self.db.flush()

        if self.settings is not None:
            from app.modules.notification_delivery.service import (
                NotificationDeliveryService,
            )
            NotificationDeliveryService(
                self.db,
                self.settings,
            ).plan_for_notification(row)

        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row

    def list_for_user(
        self,
        *,
        user_id: UUID,
        unread_only: bool,
        limit: int,
    ) -> list[NotificationResponse]:
        stmt = select(NotificationEntity).where(
            NotificationEntity.user_id == user_id
        )
        if unread_only:
            stmt = stmt.where(NotificationEntity.read_at.is_(None))
        stmt = stmt.order_by(NotificationEntity.created_at.desc()).limit(limit)
        return [
            NotificationResponse.model_validate(x)
            for x in self.db.scalars(stmt).all()
        ]

    def unread_count(self, *, user_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count(NotificationEntity.id)).where(
                    NotificationEntity.user_id == user_id,
                    NotificationEntity.read_at.is_(None),
                )
            )
            or 0
        )

    def summary(self, *, user_id: UUID) -> NotificationSummaryResponse:
        return NotificationSummaryResponse(
            unread_count=self.unread_count(user_id=user_id),
            latest=self.list_for_user(
                user_id=user_id,
                unread_only=False,
                limit=5,
            ),
        )

    def mark_read(
        self,
        *,
        user_id: UUID,
        notification_id: UUID,
    ) -> NotificationResponse:
        row = self.db.get(NotificationEntity, notification_id)
        if row is None or row.user_id != user_id:
            raise ApiError(
                404,
                "notification_not_found",
                "الإشعار غير موجود.",
            )

        if row.read_at is None:
            row.read_at = utc_now()
            self.db.commit()
            self.db.refresh(row)

        return NotificationResponse.model_validate(row)

    def mark_all_read(self, *, user_id: UUID) -> int:
        now = utc_now()
        result = self.db.execute(
            update(NotificationEntity)
            .where(
                NotificationEntity.user_id == user_id,
                NotificationEntity.read_at.is_(None),
            )
            .values(read_at=now)
        )
        self.db.commit()
        return int(result.rowcount or 0)
