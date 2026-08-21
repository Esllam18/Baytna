from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.reviews.schemas import (
    ReviewCreateRequest,
    ReviewEligibilityResponse,
    ReviewResponse,
    ReviewUpdateRequest,
)
from app.modules.reviews.service import ReviewService

router = APIRouter(prefix="/customer", tags=["reviews"])




@router.get(
    "/orders/{order_id}/review-eligibility",
    response_model=ReviewEligibilityResponse,
)
def review_eligibility(
    order_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReviewEligibilityResponse:
    return ReviewService(db).eligibility(
        customer_id=user.id,
        order_id=order_id,
    )


@router.post(
    "/orders/{order_id}/review",
    response_model=ReviewResponse,
    status_code=201,
)
def create_review(
    order_id: UUID,
    payload: ReviewCreateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    return ReviewService(db).create(
        customer_id=user.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get(
    "/orders/{order_id}/review",
    response_model=ReviewResponse,
)
def review_for_order(
    order_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    return ReviewService(db).for_order(
        customer_id=user.id,
        order_id=order_id,
    )


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
)
def update_review(
    review_id: UUID,
    payload: ReviewUpdateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    return ReviewService(db).update(
        customer_id=user.id,
        review_id=review_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("/reviews", response_model=list[ReviewResponse])
def my_reviews(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ReviewResponse]:
    return ReviewService(db).my_reviews(customer_id=user.id)
