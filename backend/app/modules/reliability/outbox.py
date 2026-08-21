from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import OutboxEventEntity
from app.core.security import utc_now

logger = logging.getLogger("baytna.outbox")


class OutboxPublisher:
    def publish(self, event: OutboxEventEntity) -> None:
        raise NotImplementedError


class LoggingOutboxPublisher(OutboxPublisher):
    def publish(self, event: OutboxEventEntity) -> None:
        logger.info(
            "domain_event %s",
            json.dumps(
                {
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "aggregate_type": event.aggregate_type,
                    "aggregate_id": event.aggregate_id,
                    "payload": event.payload_json,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )


def build_publisher(settings: Settings) -> OutboxPublisher:
    if settings.outbox_publisher == "logging":
        return LoggingOutboxPublisher()
    raise ValueError(f"Unsupported outbox publisher: {settings.outbox_publisher}")


class OutboxService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings

    def enqueue(
        self,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str | UUID,
        payload: dict,
        dedupe_key: str,
        available_at=None,
        max_attempts: int | None = None,
    ) -> OutboxEventEntity:
        existing = self.db.scalar(
            select(OutboxEventEntity).where(
                OutboxEventEntity.dedupe_key == dedupe_key
            )
        )
        if existing is not None:
            return existing

        configured = (
            max_attempts
            or (self.settings.outbox_max_attempts if self.settings else 8)
        )
        row = OutboxEventEntity(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload_json=payload,
            dedupe_key=dedupe_key,
            status="pending",
            attempts=0,
            max_attempts=configured,
            available_at=available_at or utc_now(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def recover_stale(self, *, stale_seconds: int) -> int:
        cutoff = utc_now() - timedelta(seconds=stale_seconds)
        rows = list(
            self.db.scalars(
                select(OutboxEventEntity).where(
                    OutboxEventEntity.status == "processing",
                    OutboxEventEntity.locked_at.is_not(None),
                    OutboxEventEntity.locked_at <= cutoff,
                )
            ).all()
        )
        for row in rows:
            row.status = "retry"
            row.locked_at = None
            row.locked_by = None
            row.last_error = "stale_processing_lock_recovered"
            row.available_at = utc_now()
        if rows:
            self.db.commit()
        return len(rows)

    def claim_one(self, *, worker_id: str) -> OutboxEventEntity | None:
        now = utc_now()
        stmt = (
            select(OutboxEventEntity)
            .where(
                OutboxEventEntity.status.in_(["pending", "retry"]),
                OutboxEventEntity.available_at <= now,
            )
            .order_by(OutboxEventEntity.created_at.asc())
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

    def mark_published(self, event_id: UUID) -> None:
        row = self.db.get(OutboxEventEntity, event_id)
        if row is None:
            return
        row.status = "published"
        row.published_at = utc_now()
        row.locked_at = None
        row.locked_by = None
        row.last_error = None
        self.db.commit()

    def mark_failed(self, event_id: UUID, exc: Exception) -> None:
        row = self.db.get(OutboxEventEntity, event_id)
        if row is None:
            return
        row.last_error = str(exc)[:4000]
        row.locked_at = None
        row.locked_by = None
        if row.attempts >= row.max_attempts:
            row.status = "dead_letter"
        else:
            row.status = "retry"
            base = self.settings.retry_base_seconds if self.settings else 5
            delay = min(3600, base * (2 ** max(0, row.attempts - 1)))
            row.available_at = utc_now() + timedelta(seconds=delay)
        self.db.commit()

    def publish_due(
        self,
        *,
        worker_id: str,
        publisher: OutboxPublisher,
        limit: int,
    ) -> dict:
        published = 0
        failed = 0
        for _ in range(limit):
            row = self.claim_one(worker_id=worker_id)
            if row is None:
                break
            try:
                publisher.publish(row)
                self.mark_published(row.id)
                published += 1
            except Exception as exc:
                self.db.rollback()
                self.mark_failed(row.id, exc)
                failed += 1
        return {"published": published, "failed": failed}

    def counts(self) -> dict[str, int]:
        rows = self.db.execute(
            select(OutboxEventEntity.status, func.count(OutboxEventEntity.id))
            .group_by(OutboxEventEntity.status)
        ).all()
        result = {status: int(count) for status, count in rows}
        for key in ["pending", "processing", "retry", "published", "dead_letter"]:
            result.setdefault(key, 0)
        return result
