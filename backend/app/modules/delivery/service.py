from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    DeliveryTaskEntity,
    MediaAssetEntity,
    DriverProfileEntity,
    OrderEntity,
    OrderStatusEventEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.delivery.repository import DeliveryRepository
from app.modules.delivery_timing.service import DeliveryTimingService
from app.modules.loyalty.service import LoyaltyService
from app.modules.notifications.service import NotificationService
from app.modules.reliability.outbox import OutboxService
from app.modules.delivery.schemas import (
    DeliveryAddressResponse,
    DeliveryIssueRequest,
    DeliveryMissionResponse,
    DeliveryProofRequest,
    DeliveryTrackingResponse,
    DriverStatusResponse,
)


class DeliveryService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings
        self.repo = DeliveryRepository(db)
        self.audit = AuditRepository(db)

    # --------------------------------------------------------------
    # Driver profile / availability
    # --------------------------------------------------------------
    def _profile(self, driver_id: UUID) -> DriverProfileEntity:
        profile = self.repo.driver_profile(driver_id)
        if profile is None:
            raise ApiError(
                403,
                "driver_profile_missing",
                "ملف المندوب غير موجود أو غير معتمد.",
            )
        return profile

    def status(self, *, driver_id: UUID) -> DriverStatusResponse:
        profile = self._profile(driver_id)
        active = self.repo.active_task_for_driver(driver_id)
        return DriverStatusResponse(
            driver_id=driver_id,
            status=profile.status,
            rating=profile.rating,
            active_mission_id=active.id if active else None,
        )

    def set_availability(
        self,
        *,
        driver_id: UUID,
        available: bool,
        request_id: str | None,
    ) -> DriverStatusResponse:
        profile = self._profile(driver_id)
        active = self.repo.active_task_for_driver(driver_id)

        if active is not None and not available:
            raise ApiError(
                409,
                "driver_has_active_mission",
                "لا يمكن إيقاف التوفر أثناء وجود مهمة نشطة.",
            )

        if active is not None:
            profile.status = "on_mission"
        else:
            profile.status = "available" if available else "offline"

        self.audit.add(
            action="driver.availability.changed",
            actor_user_id=driver_id,
            entity_type="driver_profile",
            entity_id=str(driver_id),
            request_id=request_id,
            metadata={"status": profile.status},
        )
        self.db.commit()
        return self.status(driver_id=driver_id)

    # --------------------------------------------------------------
    # Task creation / reads
    # --------------------------------------------------------------
    def ensure_task_for_ready_order(self, *, order_id: UUID) -> DeliveryTaskEntity:
        order = self.repo.order(order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        existing = self.repo.task_for_order(order.id)
        if existing is not None:
            return existing

        if order.status != "ready_for_pickup":
            raise ApiError(
                409,
                "delivery_task_not_ready",
                "الطلب غير جاهز لإنشاء مهمة توصيل.",
            )

        task = DeliveryTaskEntity(
            order_id=order.id,
            chef_id=order.chef_id,
            status="unassigned",
        )
        self.db.add(task)
        self.db.flush()
        return task

    def sync_ready_orders(self) -> None:
        ready = list(
            self.db.scalars(
                select(OrderEntity).where(
                    OrderEntity.status == "ready_for_pickup"
                )
            ).all()
        )
        created = False
        for order in ready:
            if self.repo.task_for_order(order.id) is None:
                self.ensure_task_for_ready_order(order_id=order.id)
                created = True
        if created:
            self.db.commit()

    def available_missions(
        self,
        *,
        driver_id: UUID,
    ) -> list[DeliveryMissionResponse]:
        profile = self._profile(driver_id)
        active = self.repo.active_task_for_driver(driver_id)

        if active is not None:
            return []

        if profile.status != "available":
            raise ApiError(
                409,
                "driver_not_available",
                "فعّل حالة التوفر أولًا لرؤية المهام الجديدة.",
            )

        self.sync_ready_orders()
        return [
            self._mission_response(task)
            for task in self.repo.available_tasks()
        ]

    def available_mission_detail(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
    ) -> DeliveryMissionResponse:
        profile = self._profile(driver_id)
        active = self.repo.active_task_for_driver(driver_id)
        if active is not None:
            raise ApiError(
                409,
                "driver_has_active_mission",
                "لديك مهمة نشطة بالفعل.",
            )
        if profile.status != "available":
            raise ApiError(
                409,
                "driver_not_available",
                "فعّل حالة التوفر أولًا.",
            )

        self.sync_ready_orders()
        task = self.repo.task(task_id)
        if (
            task is None
            or task.status != "unassigned"
            or task.driver_id is not None
        ):
            raise ApiError(
                404,
                "available_mission_not_found",
                "المهمة لم تعد متاحة.",
            )
        return self._mission_response(task)

    def current_mission(
        self,
        *,
        driver_id: UUID,
    ) -> DeliveryMissionResponse:
        self._profile(driver_id)
        task = self.repo.active_task_for_driver(driver_id)
        if task is None:
            raise ApiError(404, "active_mission_not_found", "لا توجد مهمة نشطة.")
        return self._mission_response(task)

    def history(
        self,
        *,
        driver_id: UUID,
    ) -> list[DeliveryMissionResponse]:
        self._profile(driver_id)
        return [
            self._mission_response(x)
            for x in self.repo.history_for_driver(driver_id)
        ]

    def mission_detail(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
    ) -> DeliveryMissionResponse:
        task = self.repo.task(task_id)
        if task is None or task.driver_id != driver_id:
            raise ApiError(404, "mission_not_found", "المهمة غير موجودة.")
        return self._mission_response(task)

    def _mission_response(self, task: DeliveryTaskEntity) -> DeliveryMissionResponse:
        order = self.repo.order(task.order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        chef = self.repo.chef(task.chef_id)
        if chef is None:
            raise ApiError(404, "chef_not_found", "بيانات الشيف غير موجودة.")

        address = self.repo.delivery_address(order.id)
        dropoff = None
        if address is not None:
            dropoff = DeliveryAddressResponse(
                label=address.label,
                area=address.area,
                street=address.street,
                building=address.building,
                floor=address.floor,
                apartment=address.apartment,
                latitude=address.latitude,
                longitude=address.longitude,
            )

        return DeliveryMissionResponse(
            id=task.id,
            order_id=order.id,
            chef_id=task.chef_id,
            driver_id=task.driver_id,
            status=task.status,
            order_status=order.status,
            service_date=order.service_date,
            total_minor=order.total_minor,
            currency=order.currency,
            pickup_name=chef.display_name,
            pickup_area=chef.area,
            dropoff=dropoff,
            navigation_ready=address is not None,
            accepted_at=task.accepted_at,
            arrived_pickup_at=task.arrived_pickup_at,
            picked_up_at=task.picked_up_at,
            route_started_at=task.route_started_at,
            delivered_at=task.delivered_at,
            promised_delivery_window_start_at=(ensure_utc(order.promised_delivery_window_start_at) if order.promised_delivery_window_start_at else None),
            promised_delivery_window_end_at=(ensure_utc(order.promised_delivery_window_end_at) if order.promised_delivery_window_end_at else None),
            promised_delivery_timezone=order.promised_delivery_timezone,
            delivery_timing_status=task.delivery_timing_status,
            late_by_minutes=task.late_by_minutes,
            delivery_proof_type=task.delivery_proof_type,
            delivery_proof_media_asset_id=task.delivery_proof_media_asset_id,
            issue_code=task.issue_code,
            issue_note=task.issue_note,
            created_at=task.created_at,
        )

    # --------------------------------------------------------------
    # Driver transitions
    # --------------------------------------------------------------
    def accept_mission(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        profile = self._profile(driver_id)

        if profile.status != "available":
            raise ApiError(
                409,
                "driver_not_available",
                "المندوب يجب أن يكون متاحًا لقبول مهمة جديدة.",
            )

        if self.repo.active_task_for_driver(driver_id) is not None:
            raise ApiError(
                409,
                "driver_has_active_mission",
                "لا يمكن قبول أكثر من مهمة نشطة في نفس الوقت.",
            )

        task = self.repo.task(task_id)
        if task is None:
            raise ApiError(404, "mission_not_found", "المهمة غير موجودة.")

        order = self.repo.order(task.order_id)
        if order is None or order.status != "ready_for_pickup":
            raise ApiError(
                409,
                "order_not_ready_for_driver",
                "الطلب لم يعد جاهزًا للاستلام.",
            )

        if self.repo.delivery_address(order.id) is None:
            raise ApiError(
                409,
                "delivery_address_missing",
                "لا يمكن قبول المهمة قبل تحديد عنوان توصيل العميل.",
            )

        if not self.repo.claim_task(
            task_id=task.id,
            driver_id=driver_id,
        ):
            self.db.rollback()
            raise ApiError(
                409,
                "mission_already_claimed",
                "المهمة تم قبولها بواسطة مندوب آخر.",
            )

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="ready_for_pickup",
            new_status="assigned_to_driver",
        ):
            self.db.rollback()
            raise ApiError(
                409,
                "order_state_changed",
                "تغيرت حالة الطلب أثناء قبول المهمة.",
            )

        task = self.repo.task(task.id)
        task.accepted_at = utc_now()
        profile.status = "on_mission"

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="ready_for_pickup",
                to_status="assigned_to_driver",
                actor_user_id=driver_id,
                reason="driver_assigned",
            )
        )
        self.audit.add(
            action="driver.mission.accepted",
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
            metadata={"order_id": str(order.id)},
        )
        NotificationService(self.db, self.settings).emit(
            user_id=order.customer_id,
            kind="driver_assigned",
            title="المندوب في طريقه للشيف",
            body="تم تعيين مندوب لاستلام طلبك.",
            dedupe_key=f"driver-assigned:{order.id}",
            action_url=f"/orders/{order.id}/delivery-tracking",
            data_json={"order_id": str(order.id)},
        )
        self.db.commit()
        self.db.refresh(task)
        return self._mission_response(task)

    def arrive_pickup(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        return self._task_only_transition(
            driver_id=driver_id,
            task_id=task_id,
            expected="to_pickup",
            new="at_pickup",
            timestamp_field="arrived_pickup_at",
            action="driver.mission.arrived_pickup",
            request_id=request_id,
        )

    def confirm_pickup(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        task = self._owned_task(driver_id=driver_id, task_id=task_id)
        order = self.repo.order(task.order_id)

        if task.status == "picked_up" and order.status == "picked_up":
            return self._mission_response(task)

        if task.status != "at_pickup" or order.status != "assigned_to_driver":
            raise ApiError(
                409,
                "pickup_invalid_transition",
                "يجب الوصول إلى موقع الشيف قبل تأكيد الاستلام.",
            )

        if not self.repo.transition_task(
            task_id=task.id,
            driver_id=driver_id,
            expected_status="at_pickup",
            new_status="picked_up",
        ):
            self.db.rollback()
            raise ApiError(409, "mission_state_changed", "تغيرت حالة المهمة.")

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="assigned_to_driver",
            new_status="picked_up",
        ):
            self.db.rollback()
            raise ApiError(409, "order_state_changed", "تغيرت حالة الطلب.")

        task = self.repo.task(task.id)
        task.picked_up_at = utc_now()

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="assigned_to_driver",
                to_status="picked_up",
                actor_user_id=driver_id,
                reason="driver_picked_up",
            )
        )
        self.audit.add(
            action="driver.mission.picked_up",
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
        )
        NotificationService(self.db, self.settings).emit(
            user_id=order.customer_id,
            kind="order_picked_up",
            title="المندوب استلم الطلب",
            body="طلبك خرج من عند الشيف.",
            dedupe_key=f"order-picked-up:{order.id}",
            action_url=f"/orders/{order.id}/delivery-tracking",
            data_json={"order_id": str(order.id)},
        )
        self.db.commit()
        return self._mission_response(task)

    def start_delivery(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        task = self._owned_task(driver_id=driver_id, task_id=task_id)
        order = self.repo.order(task.order_id)

        if task.status == "to_customer" and order.status == "out_for_delivery":
            return self._mission_response(task)

        if task.status != "picked_up" or order.status != "picked_up":
            raise ApiError(
                409,
                "delivery_invalid_transition",
                "يجب استلام الطلب أولًا قبل بدء التوصيل.",
            )

        if not self.repo.transition_task(
            task_id=task.id,
            driver_id=driver_id,
            expected_status="picked_up",
            new_status="to_customer",
        ):
            self.db.rollback()
            raise ApiError(409, "mission_state_changed", "تغيرت حالة المهمة.")

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="picked_up",
            new_status="out_for_delivery",
        ):
            self.db.rollback()
            raise ApiError(409, "order_state_changed", "تغيرت حالة الطلب.")

        task = self.repo.task(task.id)
        task.route_started_at = utc_now()

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="picked_up",
                to_status="out_for_delivery",
                actor_user_id=driver_id,
                reason="delivery_started",
            )
        )
        self.audit.add(
            action="driver.mission.out_for_delivery",
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._mission_response(task)

    def mark_delivered(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        proof: DeliveryProofRequest,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        task = self._owned_task(driver_id=driver_id, task_id=task_id)
        order = self.repo.order(task.order_id)
        profile = self._profile(driver_id)

        if task.status == "delivered" and order.status == "delivered":
            return self._mission_response(task)

        if proof.proof_type == "photo" and proof.media_asset_id is not None:
            asset = self.db.get(MediaAssetEntity, proof.media_asset_id)
            if asset is None or asset.owner_user_id != driver_id or asset.status != "ready" or asset.purpose != "delivery_proof":
                raise ApiError(404, "delivery_proof_media_not_found", "صورة إثبات التوصيل غير موجودة أو غير جاهزة.")
        else:
            asset = None

        if task.status != "to_customer" or order.status != "out_for_delivery":
            raise ApiError(
                409,
                "delivery_complete_invalid_transition",
                "لا يمكن إتمام المهمة قبل بدء التوصيل للعميل.",
            )

        if not self.repo.transition_task(
            task_id=task.id,
            driver_id=driver_id,
            expected_status="to_customer",
            new_status="delivered",
        ):
            self.db.rollback()
            raise ApiError(409, "mission_state_changed", "تغيرت حالة المهمة.")

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="out_for_delivery",
            new_status="delivered",
        ):
            self.db.rollback()
            raise ApiError(409, "order_state_changed", "تغيرت حالة الطلب.")

        task = self.repo.task(task.id)
        task.delivered_at = utc_now()
        if self.settings is not None:
            timing = DeliveryTimingService(self.settings).stamp_task(
                order=order,
                task=task,
                delivered_at=task.delivered_at,
            )
        else:
            task.delivery_timing_status = "unmeasurable"
            task.late_by_minutes = None
            timing = None
        task.delivery_proof_type = proof.proof_type
        task.delivery_proof_reference = proof.proof_reference or (str(proof.media_asset_id) if proof.media_asset_id else None)
        task.delivery_proof_media_asset_id = asset.id if asset is not None else None
        profile.status = "available"

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="out_for_delivery",
                to_status="delivered",
                actor_user_id=driver_id,
                reason="proof_of_delivery_recorded",
            )
        )
        self.audit.add(
            action="driver.mission.delivered",
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
            metadata={
                "proof_type": proof.proof_type,
                "order_id": str(order.id),
                "delivery_timing_status": task.delivery_timing_status,
                "late_by_minutes": task.late_by_minutes,
                "promised_delivery_window_end_at": (
                    order.promised_delivery_window_end_at.isoformat()
                    if order.promised_delivery_window_end_at
                    else None
                ),
            },
        )
        NotificationService(self.db, self.settings).emit(
            user_id=order.customer_id,
            kind="order_delivered",
            title="تم توصيل طلبك",
            body="بالهنا والشفا! تقدر دلوقتي تقيّم تجربتك.",
            dedupe_key=f"order-delivered:{order.id}",
            action_url=f"/orders/{order.id}/review",
            data_json={
                "order_id": str(order.id),
                "delivery_timing_status": task.delivery_timing_status,
                "late_by_minutes": task.late_by_minutes,
            },
        )
        OutboxService(self.db, self.settings).enqueue(
            event_type="order.delivered",
            aggregate_type="order",
            aggregate_id=order.id,
            dedupe_key=f"order.delivered:{order.id}",
            payload={
                "order_id": str(order.id),
                "customer_id": str(order.customer_id),
                "chef_id": str(order.chef_id),
                "driver_id": str(driver_id),
                "total_minor": order.total_minor,
                "currency": order.currency,
                "delivery_timing_status": task.delivery_timing_status,
                "late_by_minutes": task.late_by_minutes,
                "promised_delivery_window_end_at": (
                    order.promised_delivery_window_end_at.isoformat()
                    if order.promised_delivery_window_end_at
                    else None
                ),
            },
        )
        if self.settings is not None:
            LoyaltyService(self.db, self.settings).award_for_delivered_order(
                order=order,
                request_id=request_id,
                commit=False,
            )
        self.db.commit()
        return self._mission_response(task)

    def report_issue(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        payload: DeliveryIssueRequest,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        task = self._owned_task(driver_id=driver_id, task_id=task_id)

        if task.status == "delivery_issue":
            return self._mission_response(task)

        if task.status not in {
            "to_pickup",
            "at_pickup",
            "picked_up",
            "to_customer",
        }:
            raise ApiError(
                409,
                "delivery_issue_invalid_state",
                "لا يمكن تسجيل مشكلة في المرحلة الحالية.",
            )

        previous = task.status
        if not self.repo.transition_task(
            task_id=task.id,
            driver_id=driver_id,
            expected_status=previous,
            new_status="delivery_issue",
        ):
            self.db.rollback()
            raise ApiError(409, "mission_state_changed", "تغيرت حالة المهمة.")

        task = self.repo.task(task.id)
        task.issue_from_status = previous
        task.issue_code = payload.issue_code
        task.issue_note = payload.note

        self.audit.add(
            action="driver.mission.issue_reported",
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
            metadata={
                "issue_code": payload.issue_code,
                "from_status": previous,
            },
        )
        self.db.commit()
        return self._mission_response(task)

    def resume_after_issue(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        task = self._owned_task(driver_id=driver_id, task_id=task_id)
        if task.status != "delivery_issue" or not task.issue_from_status:
            raise ApiError(
                409,
                "delivery_issue_not_active",
                "لا توجد مشكلة نشطة يمكن استئناف المهمة بعدها.",
            )

        restore = task.issue_from_status
        if restore not in {"to_pickup", "at_pickup", "picked_up", "to_customer"}:
            raise ApiError(
                409,
                "delivery_issue_restore_invalid",
                "تعذر استعادة مرحلة المهمة السابقة.",
            )

        if not self.repo.transition_task(
            task_id=task.id,
            driver_id=driver_id,
            expected_status="delivery_issue",
            new_status=restore,
        ):
            self.db.rollback()
            raise ApiError(409, "mission_state_changed", "تغيرت حالة المهمة.")

        task = self.repo.task(task.id)
        task.issue_from_status = None
        task.issue_code = None
        task.issue_note = None

        self.audit.add(
            action="driver.mission.issue_resolved",
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
            metadata={"restored_status": restore},
        )
        self.db.commit()
        return self._mission_response(task)

    def _owned_task(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
    ) -> DeliveryTaskEntity:
        task = self.repo.task(task_id)
        if task is None or task.driver_id != driver_id:
            raise ApiError(404, "mission_not_found", "المهمة غير موجودة.")
        return task

    def _task_only_transition(
        self,
        *,
        driver_id: UUID,
        task_id: UUID,
        expected: str,
        new: str,
        timestamp_field: str,
        action: str,
        request_id: str | None,
    ) -> DeliveryMissionResponse:
        task = self._owned_task(driver_id=driver_id, task_id=task_id)
        if task.status == new:
            return self._mission_response(task)

        if task.status != expected:
            raise ApiError(
                409,
                "mission_invalid_transition",
                "لا يمكن نقل المهمة إلى المرحلة المطلوبة.",
            )

        if not self.repo.transition_task(
            task_id=task.id,
            driver_id=driver_id,
            expected_status=expected,
            new_status=new,
        ):
            self.db.rollback()
            raise ApiError(409, "mission_state_changed", "تغيرت حالة المهمة.")

        task = self.repo.task(task.id)
        setattr(task, timestamp_field, utc_now())

        self.audit.add(
            action=action,
            actor_user_id=driver_id,
            entity_type="delivery_task",
            entity_id=str(task.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._mission_response(task)

    # --------------------------------------------------------------
    # Customer delivery tracking
    # --------------------------------------------------------------
    def customer_tracking(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
    ) -> DeliveryTrackingResponse:
        order = self.repo.order(order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        task = self.repo.task_for_order(order.id)

        labels = {
            "ready_for_pickup": ("أكلك جاهز", "في انتظار تعيين المندوب."),
            "assigned_to_driver": (
                "المندوب في طريقه للشيف",
                "تم تعيين مندوب لاستلام طلبك.",
            ),
            "picked_up": (
                "المندوب استلم الطلب",
                "تم استلام الطلب من الشيف.",
            ),
            "out_for_delivery": (
                "طلبك في الطريق",
                "المندوب متجه إلى عنوان التوصيل.",
            ),
            "delivered": (
                "تم توصيل طلبك",
                "تم تسجيل إثبات التوصيل بنجاح.",
            ),
        }

        display, detail = labels.get(
            order.status,
            ("جاري تحديث حالة التوصيل", None),
        )

        if task is not None and task.status == "delivery_issue":
            display = "يوجد تحديث في التوصيل"
            detail = "تم تسجيل مشكلة أثناء التوصيل وجارٍ التعامل معها."

        return DeliveryTrackingResponse(
            order_id=order.id,
            order_status=order.status,
            mission_status=task.status if task else None,
            display_status=display,
            detail=detail,
            delivered_at=task.delivered_at if task else None,
            promised_delivery_window_start_at=(ensure_utc(order.promised_delivery_window_start_at) if order.promised_delivery_window_start_at else None),
            promised_delivery_window_end_at=(ensure_utc(order.promised_delivery_window_end_at) if order.promised_delivery_window_end_at else None),
            promised_delivery_timezone=order.promised_delivery_timezone,
            delivery_timing_status=task.delivery_timing_status if task else None,
            late_by_minutes=task.late_by_minutes if task else None,
        )
