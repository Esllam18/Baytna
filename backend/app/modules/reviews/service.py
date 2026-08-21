from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db_models import ChefProfileEntity, DriverProfileEntity, ReviewEntity
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import (
    ChefRatingSummaryResponse,
    DriverRatingSummaryResponse,
    ReviewCreateRequest,
    PublicReviewResponse,
    ReviewEligibilityResponse,
    ReviewResponse,
    ReviewUpdateRequest,
)


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReviewRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
        payload: ReviewCreateRequest,
        request_id: str | None,
    ) -> ReviewResponse:
        order = self.repo.order(order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        if order.status != "delivered":
            raise ApiError(
                409,
                "review_order_not_delivered",
                "يمكن تقييم الطلب بعد اكتمال التوصيل فقط.",
            )

        existing = self.repo.review_for_order(order.id)
        if existing is not None:
            raise ApiError(
                409,
                "review_already_exists",
                "تم تقييم هذا الطلب بالفعل.",
            )

        driver_id = self.repo.delivery_driver_for_order(order.id)

        review = ReviewEntity(
            order_id=order.id,
            customer_id=customer_id,
            chef_id=order.chef_id,
            driver_id=driver_id,
            **payload.model_dump(),
        )
        self.db.add(review)
        self.db.flush()

        self._refresh_aggregates(
            chef_id=order.chef_id,
            driver_id=driver_id,
        )

        self.audit.add(
            action="customer.review.created",
            actor_user_id=customer_id,
            entity_type="review",
            entity_id=str(review.id),
            request_id=request_id,
            metadata={
                "order_id": str(order.id),
                "chef_id": str(order.chef_id),
                "driver_id": str(driver_id) if driver_id else None,
            },
        )
        self.db.commit()
        self.db.refresh(review)
        return ReviewResponse.model_validate(review)

    def update(
        self,
        *,
        customer_id: UUID,
        review_id: UUID,
        payload: ReviewUpdateRequest,
        request_id: str | None,
    ) -> ReviewResponse:
        review = self.repo.review(review_id)
        if review is None or review.customer_id != customer_id:
            raise ApiError(404, "review_not_found", "التقييم غير موجود.")

        values = payload.model_dump(exclude_unset=True)
        if not values:
            raise ApiError(422, "review_no_changes", "لا توجد تعديلات.")

        for key, value in values.items():
            setattr(review, key, value)

        self._refresh_aggregates(
            chef_id=review.chef_id,
            driver_id=review.driver_id,
        )

        self.audit.add(
            action="customer.review.updated",
            actor_user_id=customer_id,
            entity_type="review",
            entity_id=str(review.id),
            request_id=request_id,
            metadata={"fields": sorted(values.keys())},
        )
        self.db.commit()
        self.db.refresh(review)
        return ReviewResponse.model_validate(review)

    def for_order(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
    ) -> ReviewResponse:
        order = self.repo.order(order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        review = self.repo.review_for_order(order.id)
        if review is None:
            raise ApiError(404, "review_not_found", "لم يتم تقييم الطلب بعد.")
        return ReviewResponse.model_validate(review)

    def my_reviews(self, *, customer_id: UUID) -> list[ReviewResponse]:
        return [
            ReviewResponse.model_validate(x)
            for x in self.repo.customer_reviews(customer_id)
        ]

    def public_reviews(
        self,
        *,
        chef_id: UUID,
    ) -> list[PublicReviewResponse]:
        return [
            PublicReviewResponse.model_validate(x)
            for x in self.repo.visible_for_chef(chef_id)
        ]

    def eligibility(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
    ) -> ReviewEligibilityResponse:
        order = self.repo.order(order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        review = self.repo.review_for_order(order.id)
        if review is not None:
            return ReviewEligibilityResponse(
                order_id=order.id,
                order_status=order.status,
                can_review=True,
                reason="review_exists",
                review=ReviewResponse.model_validate(review),
            )

        if order.status != "delivered":
            return ReviewEligibilityResponse(
                order_id=order.id,
                order_status=order.status,
                can_review=False,
                reason="order_not_delivered",
                review=None,
            )

        return ReviewEligibilityResponse(
            order_id=order.id,
            order_status=order.status,
            can_review=True,
            reason="ready_for_review",
            review=None,
        )

    def chef_summary(self, *, chef_id: UUID) -> ChefRatingSummaryResponse:
        chef = self.db.get(ChefProfileEntity, chef_id)
        if chef is None:
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")

        values = self.repo.recalc_chef_rating(chef_id)
        return ChefRatingSummaryResponse(
            chef_id=chef_id,
            rating=round(values["overall"], 2),
            review_count=values["count"],
            food_quality=round(values["food_quality"], 2),
            packaging=round(values["packaging"], 2),
            order_accuracy=round(values["order_accuracy"], 2),
            value_for_money=round(values["value_for_money"], 2),
        )

    def driver_summary(self, *, driver_id: UUID) -> DriverRatingSummaryResponse:
        driver = self.db.get(DriverProfileEntity, driver_id)
        if driver is None:
            raise ApiError(404, "driver_not_found", "المندوب غير موجود.")
        values = self.repo.recalc_driver_rating(driver_id)
        return DriverRatingSummaryResponse(
            driver_id=driver_id,
            rating=round(values["overall"], 2),
            review_count=values["count"],
        )

    def moderate(
        self,
        *,
        admin_id: UUID,
        review_id: UUID,
        is_visible: bool,
        moderation_note: str | None,
        request_id: str | None,
    ) -> ReviewResponse:
        review = self.repo.review(review_id)
        if review is None:
            raise ApiError(404, "review_not_found", "التقييم غير موجود.")

        review.is_visible = is_visible
        review.moderation_note = moderation_note

        self._refresh_aggregates(
            chef_id=review.chef_id,
            driver_id=review.driver_id,
        )

        self.audit.add(
            action="admin.review.moderated",
            actor_user_id=admin_id,
            entity_type="review",
            entity_id=str(review.id),
            request_id=request_id,
            metadata={"is_visible": is_visible},
        )
        self.db.commit()
        self.db.refresh(review)
        return ReviewResponse.model_validate(review)

    def _refresh_aggregates(
        self,
        *,
        chef_id: UUID,
        driver_id: UUID | None,
    ) -> None:
        chef = self.db.get(ChefProfileEntity, chef_id)
        if chef is not None:
            values = self.repo.recalc_chef_rating(chef_id)
            chef.rating = round(values["overall"], 2) if values["count"] else 0.0

        if driver_id is not None:
            driver = self.db.get(DriverProfileEntity, driver_id)
            if driver is not None:
                values = self.repo.recalc_driver_rating(driver_id)
                driver.rating = round(values["overall"], 2) if values["count"] else 0.0

        self.db.flush()
