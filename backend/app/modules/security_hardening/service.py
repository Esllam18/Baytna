from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import RateLimitBucketEntity, SecurityEventEntity
from app.core.errors import ApiError
from app.core.security import utc_now


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    count: int


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
            if candidate:
                return candidate
        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class SecurityService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def hash_key(self, value: str) -> str:
        return _sha256(value)

    def record_event(
        self,
        *,
        event_type: str,
        severity: str = "info",
        request_id: str | None = None,
        actor_user_id: UUID | None = None,
        ip: str | None = None,
        path: str | None = None,
        metadata: dict | None = None,
        commit: bool = False,
    ) -> SecurityEventEntity:
        row = SecurityEventEntity(
            event_type=event_type,
            severity=severity,
            request_id=request_id,
            actor_user_id=actor_user_id,
            ip_hash=self.hash_key(ip) if ip else None,
            path=path,
            metadata_json=metadata or {},
        )
        self.db.add(row)
        self.db.flush()
        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row

    def consume(
        self,
        *,
        scope: str,
        raw_key: str,
        limit: int,
        window_seconds: int | None = None,
    ) -> RateLimitDecision:
        if limit <= 0:
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=0,
                retry_after_seconds=0,
                count=0,
            )

        window_seconds = window_seconds or self.settings.rate_limit_window_seconds
        now = utc_now()
        epoch = int(now.timestamp())
        window_epoch = epoch - (epoch % window_seconds)
        window_start = datetime.fromtimestamp(window_epoch, tz=timezone.utc)
        expires_at = window_start + timedelta(seconds=window_seconds)
        key_hash = self.hash_key(raw_key)

        values = {
            "scope": scope,
            "key_hash": key_hash,
            "window_start": window_start,
            "window_seconds": window_seconds,
            "request_count": 1,
            "expires_at": expires_at,
        }

        dialect = self.db.bind.dialect.name if self.db.bind is not None else ""
        if dialect == "postgresql":
            stmt = pg_insert(RateLimitBucketEntity).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["scope", "key_hash", "window_start"],
                set_={
                    "request_count": RateLimitBucketEntity.request_count + 1,
                    "updated_at": now,
                    "expires_at": expires_at,
                },
            ).returning(RateLimitBucketEntity.request_count)
            count = int(self.db.scalar(stmt))
        elif dialect == "sqlite":
            stmt = sqlite_insert(RateLimitBucketEntity).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["scope", "key_hash", "window_start"],
                set_={
                    "request_count": RateLimitBucketEntity.request_count + 1,
                    "updated_at": now,
                    "expires_at": expires_at,
                },
            ).returning(RateLimitBucketEntity.request_count)
            count = int(self.db.scalar(stmt))
        else:
            row = self.db.scalar(
                select(RateLimitBucketEntity).where(
                    RateLimitBucketEntity.scope == scope,
                    RateLimitBucketEntity.key_hash == key_hash,
                    RateLimitBucketEntity.window_start == window_start,
                )
            )
            if row is None:
                row = RateLimitBucketEntity(**values)
                self.db.add(row)
                self.db.flush()
                count = 1
            else:
                row.request_count += 1
                row.expires_at = expires_at
                self.db.flush()
                count = row.request_count

        remaining = max(0, limit - count)
        retry_after = max(1, int((expires_at - now).total_seconds()))
        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=retry_after,
            count=count,
        )

    def enforce(
        self,
        *,
        request: Request,
        scope: str,
        raw_key: str,
        limit: int,
        event_type: str = "rate_limit.blocked",
    ) -> RateLimitDecision:
        decision = self.consume(
            scope=scope,
            raw_key=raw_key,
            limit=limit,
        )

        if decision.allowed:
            self.db.commit()
            return decision

        ip = client_ip(request, self.settings)
        self.record_event(
            event_type=event_type,
            severity="warning",
            request_id=getattr(request.state, "request_id", None),
            ip=ip,
            path=request.url.path,
            metadata={
                "scope": scope,
                "limit": limit,
                "window_seconds": self.settings.rate_limit_window_seconds,
                "key_hash": self.hash_key(raw_key),
            },
        )
        self.db.commit()

        raise ApiError(
            429,
            "rate_limit_exceeded",
            "تم تجاوز عدد المحاولات المسموح به. حاول مرة أخرى لاحقًا.",
            {
                "scope": scope,
                "limit": limit,
                "retry_after_seconds": decision.retry_after_seconds,
            },
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    def enforce_auth_phone_and_ip(
        self,
        *,
        request: Request,
        phone: str,
        operation: str,
        ip_limit: int,
        phone_limit: int,
    ) -> None:
        ip = client_ip(request, self.settings)
        self.enforce(
            request=request,
            scope=f"auth.{operation}.ip",
            raw_key=ip,
            limit=ip_limit,
        )
        self.enforce(
            request=request,
            scope=f"auth.{operation}.phone",
            raw_key=phone,
            limit=phone_limit,
        )

    def cleanup(self) -> dict[str, int]:
        now = utc_now()
        security_cutoff = now - timedelta(
            days=self.settings.security_event_retention_days
        )
        bucket_result = self.db.execute(
            delete(RateLimitBucketEntity).where(
                RateLimitBucketEntity.expires_at
                <= now - timedelta(minutes=self.settings.rate_limit_retention_minutes)
            )
        )
        event_result = self.db.execute(
            delete(SecurityEventEntity).where(
                SecurityEventEntity.created_at <= security_cutoff
            )
        )
        self.db.commit()
        return {
            "deleted_rate_limit_buckets": int(bucket_result.rowcount or 0),
            "deleted_security_events": int(event_result.rowcount or 0),
        }
