from fastapi import APIRouter, Depends

from app.core.auth import require_roles
from app.core.db_models import UserEntity
from app.core.models import UserRole

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, str]:
    return {"status": "ok", "role": "admin"}
