from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.models import PublicUser, UserRole
from app.core.repositories import AuditRepository, AuthRepository, UserRepository
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    ensure_utc,
    hash_secret,
    utc_now,
    verify_secret,
)
from app.modules.auth.schemas import SendOtpResponse, TokenResponse


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)
        self.auth = AuthRepository(db)
        self.audit = AuditRepository(db)

    def send_otp(self, phone: str, request_id: str | None = None) -> SendOtpResponse:
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = hash_secret(code, self.settings.otp_pepper)

        challenge = self.auth.create_otp(
            phone=phone,
            code_hash=code_hash,
            ttl_seconds=self.settings.otp_ttl_seconds,
        )
        self.audit.add(
            action="auth.otp.created",
            entity_type="phone",
            entity_id=phone,
            request_id=request_id,
        )
        self.db.commit()

        return SendOtpResponse(
            challenge_expires_at=challenge.expires_at,
            development_otp=(
                code
                if self.settings.env == "development"
                and self.settings.dev_return_otp
                else None
            ),
        )

    def verify_otp(
        self,
        phone: str,
        code: str,
        request_id: str | None = None,
    ) -> TokenResponse:
        challenge = self.auth.latest_open_otp(phone)

        if challenge is None:
            raise ApiError(400, "otp_missing", "لا يوجد كود تحقق صالح لهذا الرقم.")

        now = utc_now()
        if ensure_utc(challenge.expires_at) <= now:
            self.auth.consume_otp(challenge)
            self.db.commit()
            raise ApiError(400, "otp_expired", "انتهت صلاحية كود التحقق.")

        challenge.attempts += 1

        if challenge.attempts > self.settings.otp_max_attempts:
            self.auth.consume_otp(challenge)
            self.db.commit()
            raise ApiError(
                429,
                "otp_attempts_exceeded",
                "تم تجاوز عدد المحاولات المسموح به.",
            )

        if not verify_secret(code, challenge.code_hash, self.settings.otp_pepper):
            self.db.commit()
            raise ApiError(400, "otp_invalid", "كود التحقق غير صحيح.")

        self.auth.consume_otp(challenge)
        user = self.users.get_or_create_customer(phone)

        access_token, access_expires = create_access_token(
            user_id=user.id,
            role=UserRole(user.role),
            settings=self.settings,
        )
        refresh_token = generate_refresh_token()
        refresh_hash = hash_secret(
            refresh_token,
            self.settings.refresh_token_pepper,
        )
        db_session = self.auth.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            ttl_days=self.settings.refresh_token_ttl_days,
        )

        self.audit.add(
            action="auth.login.succeeded",
            actor_user_id=user.id,
            entity_type="auth_session",
            entity_id=str(db_session.id),
            request_id=request_id,
        )
        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expires,
            refresh_token_expires_at=db_session.expires_at,
            user=PublicUser.model_validate(user),
        )

    def refresh(
        self,
        refresh_token: str,
        request_id: str | None = None,
    ) -> TokenResponse:
        refresh_hash = hash_secret(
            refresh_token,
            self.settings.refresh_token_pepper,
        )
        old_session = self.auth.session_by_refresh_hash(refresh_hash)

        if old_session is None:
            raise ApiError(401, "refresh_invalid", "رمز التجديد غير صالح.")

        now = utc_now()
        if old_session.revoked_at is not None:
            raise ApiError(401, "refresh_revoked", "تم إلغاء رمز التجديد.")

        if ensure_utc(old_session.expires_at) <= now:
            self.auth.revoke_session(old_session)
            self.db.commit()
            raise ApiError(401, "refresh_expired", "انتهت صلاحية رمز التجديد.")

        user = self.users.get_by_id(old_session.user_id)
        if user is None or not user.is_active:
            raise ApiError(401, "auth_user_unavailable", "الحساب غير متاح.")

        new_refresh_token = generate_refresh_token()
        new_refresh_hash = hash_secret(
            new_refresh_token,
            self.settings.refresh_token_pepper,
        )
        new_session = self.auth.create_session(
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            ttl_days=self.settings.refresh_token_ttl_days,
        )
        self.auth.revoke_session(
            old_session,
            replaced_by_session_id=new_session.id,
        )

        access_token, access_expires = create_access_token(
            user_id=user.id,
            role=UserRole(user.role),
            settings=self.settings,
        )

        self.audit.add(
            action="auth.refresh.rotated",
            actor_user_id=user.id,
            entity_type="auth_session",
            entity_id=str(old_session.id),
            request_id=request_id,
            metadata={"replacement_session_id": str(new_session.id)},
        )
        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            access_token_expires_at=access_expires,
            refresh_token_expires_at=new_session.expires_at,
            user=PublicUser.model_validate(user),
        )

    def logout(
        self,
        refresh_token: str,
        request_id: str | None = None,
    ) -> None:
        refresh_hash = hash_secret(
            refresh_token,
            self.settings.refresh_token_pepper,
        )
        session = self.auth.session_by_refresh_hash(refresh_hash)

        # Idempotent logout: unknown token returns success without exposing state.
        if session is None:
            return

        if session.revoked_at is None:
            self.auth.revoke_session(session)
            self.audit.add(
                action="auth.logout",
                actor_user_id=session.user_id,
                entity_type="auth_session",
                entity_id=str(session.id),
                request_id=request_id,
            )
            self.db.commit()
