from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.reviews.schemas import (
    ChefRatingSummaryResponse,
    PublicReviewResponse,
)
from app.modules.reviews.service import ReviewService

router = APIRouter(tags=["reviews-public"])


@router.get(
    "/chefs/{chef_id}/reviews",
    response_model=list[PublicReviewResponse],
)
def chef_reviews(
    chef_id: UUID,
    db: Session = Depends(get_db),
) -> list[PublicReviewResponse]:
    return ReviewService(db).public_reviews(chef_id=chef_id)


@router.get(
    "/chefs/{chef_id}/rating-summary",
    response_model=ChefRatingSummaryResponse,
)
def chef_rating_summary(
    chef_id: UUID,
    db: Session = Depends(get_db),
) -> ChefRatingSummaryResponse:
    return ReviewService(db).chef_summary(chef_id=chef_id)
