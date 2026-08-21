from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.reviews.schemas import ModerationRequest, ReviewResponse
from app.modules.reviews.service import ReviewService

router = APIRouter(prefix="/admin/reviews", tags=["admin-reviews"])


@router.patch("/{review_id}/moderation", response_model=ReviewResponse)
def moderate_review(
    review_id: UUID,
    payload: ModerationRequest,
    request: Request,
    admin: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    return ReviewService(db).moderate(
        admin_id=admin.id,
        review_id=review_id,
        is_visible=payload.is_visible,
        moderation_note=payload.moderation_note,
        request_id=request.state.request_id,
    )
