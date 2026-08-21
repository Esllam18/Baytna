from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.core.db_models import (
    AuditLogEntity,
    AuthSessionEntity,
    ChefProfileEntity,
    CustomerProfileEntity,
    OtpChallengeEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import hash_secret, utc_now


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> UserEntity | None:
        return self.db.get(UserEntity, user_id)

    def get_by_phone(self, phone: str) -> UserEntity | None:
        return self.db.scalar(select(UserEntity).where(UserEntity.phone == phone))

    def get_or_create_customer(self, phone: str) -> UserEntity:
        user = self.get_by_phone(phone)
        if user:
            return user

        user = UserEntity(
            phone=phone,
            role=UserRole.CUSTOMER.value,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(CustomerProfileEntity(user_id=user.id))
        self.db.flush()
        return user


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def invalidate_open_otps(self, phone: str) -> None:
        now = utc_now()
        self.db.execute(
            update(OtpChallengeEntity)
            .where(
                OtpChallengeEntity.phone == phone,
                OtpChallengeEntity.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )

    def create_otp(
        self,
        *,
        phone: str,
        code_hash: str,
        ttl_seconds: int,
    ) -> OtpChallengeEntity:
        self.invalidate_open_otps(phone)
        challenge = OtpChallengeEntity(
            phone=phone,
            code_hash=code_hash,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
        )
        self.db.add(challenge)
        self.db.flush()
        return challenge

    def latest_open_otp(self, phone: str) -> OtpChallengeEntity | None:
        return self.db.scalar(
            select(OtpChallengeEntity)
            .where(
                OtpChallengeEntity.phone == phone,
                OtpChallengeEntity.consumed_at.is_(None),
            )
            .order_by(desc(OtpChallengeEntity.created_at))
            .limit(1)
        )

    def consume_otp(self, challenge: OtpChallengeEntity) -> None:
        challenge.consumed_at = utc_now()
        self.db.flush()

    def create_session(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        ttl_days: int,
    ) -> AuthSessionEntity:
        session = AuthSessionEntity(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=utc_now() + timedelta(days=ttl_days),
        )
        self.db.add(session)
        self.db.flush()
        return session

    def session_by_refresh_hash(self, refresh_hash: str) -> AuthSessionEntity | None:
        return self.db.scalar(
            select(AuthSessionEntity).where(
                AuthSessionEntity.refresh_token_hash == refresh_hash
            )
        )

    def revoke_session(
        self,
        session: AuthSessionEntity,
        *,
        replaced_by_session_id: UUID | None = None,
    ) -> None:
        session.revoked_at = utc_now()
        session.replaced_by_session_id = replaced_by_session_id
        self.db.flush()


class ChefRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        area: str | None = None,
        open_today: bool | None = None,
    ) -> list[ChefProfileEntity]:
        stmt = select(ChefProfileEntity).where(
            ChefProfileEntity.status == "active",
            ChefProfileEntity.is_verified.is_(True),
        )

        if area:
            stmt = stmt.where(ChefProfileEntity.area == area.strip())
        if open_today is not None:
            stmt = stmt.where(ChefProfileEntity.is_open_today.is_(open_today))

        stmt = stmt.order_by(ChefProfileEntity.rating.desc())
        return list(self.db.scalars(stmt).all())

    def get(self, chef_id: UUID) -> ChefProfileEntity | None:
        chef = self.db.get(ChefProfileEntity, chef_id)
        if chef is None:
            return None
        if chef.status != "active" or not chef.is_verified:
            return None
        return chef


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        action: str,
        actor_user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLogEntity:
        row = AuditLogEntity(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            metadata_json=metadata or {},
        )
        self.db.add(row)
        self.db.flush()
        return row
