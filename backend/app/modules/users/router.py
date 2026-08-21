from fastapi import APIRouter, Depends

from app.core.auth import current_user
from app.core.db_models import UserEntity
from app.core.models import PublicUser

router = APIRouter(tags=["users"])


@router.get("/me", response_model=PublicUser)
def me(user: UserEntity = Depends(current_user)) -> PublicUser:
    return PublicUser.model_validate(user)
