from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.models import UserRole
from app.core.repositories import UserRepository
from app.core.security import decode_access_token
from app.core.db_models import UserEntity


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserEntity:
    if not authorization:
        raise ApiError(401, "auth_missing", "مطلوب تسجيل الدخول.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "auth_invalid_header", "صيغة Authorization غير صحيحة.")

    payload = decode_access_token(token, settings)

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(401, "auth_access_invalid", "رمز الدخول غير صالح.") from exc

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "auth_user_unavailable", "الحساب غير متاح.")

    if payload.get("role") != user.role:
        raise ApiError(401, "auth_role_mismatch", "بيانات الجلسة لم تعد صالحة.")

    return user


def require_roles(*roles: UserRole) -> Callable:
    allowed = {role.value for role in roles}

    def dependency(user: UserEntity = Depends(current_user)) -> UserEntity:
        if user.role not in allowed:
            raise ApiError(403, "forbidden", "ليس لديك صلاحية لتنفيذ هذا الإجراء.")
        return user

    return dependency
