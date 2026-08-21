from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db_models import CustomerProfileEntity, UserEntity
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.modules.users.customer_schemas import (
    CustomerProfileResponse,
    CustomerProfileUpdateRequest,
)


class CustomerAccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditRepository(db)

    def profile(self, *, user_id: UUID) -> CustomerProfileResponse:
        user = self.db.get(UserEntity, user_id)
        if user is None:
            raise ApiError(404, "user_not_found", "المستخدم غير موجود.")

        profile = self.db.get(CustomerProfileEntity, user_id)
        if profile is None:
            profile = CustomerProfileEntity(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        return CustomerProfileResponse(
            id=user.id,
            phone=user.phone,
            display_name=profile.display_name,
            preferred_language=profile.preferred_language,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    def update_profile(
        self,
        *,
        user_id: UUID,
        payload: CustomerProfileUpdateRequest,
        request_id: str | None,
    ) -> CustomerProfileResponse:
        user = self.db.get(UserEntity, user_id)
        if user is None:
            raise ApiError(404, "user_not_found", "المستخدم غير موجود.")

        profile = self.db.get(CustomerProfileEntity, user_id)
        if profile is None:
            profile = CustomerProfileEntity(user_id=user_id)
            self.db.add(profile)
            self.db.flush()

        display_name = (
            payload.display_name.strip()
            if payload.display_name and payload.display_name.strip()
            else None
        )
        profile.display_name = display_name
        profile.preferred_language = payload.preferred_language

        self.audit.add(
            action="customer.profile.updated",
            actor_user_id=user_id,
            entity_type="customer_profile",
            entity_id=str(user_id),
            request_id=request_id,
            metadata={
                "display_name_set": bool(display_name),
                "preferred_language": payload.preferred_language,
            },
        )
        self.db.commit()
        return self.profile(user_id=user_id)
