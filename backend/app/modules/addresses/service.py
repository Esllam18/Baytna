from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings

from app.core.db_models import (
    AddressEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.modules.launch_governance.service import LaunchTrafficGovernanceService
from app.modules.addresses.schemas import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
)


class AddressService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditRepository(db)

    def list_addresses(self, *, customer_id: UUID) -> list[AddressResponse]:
        rows = list(
            self.db.scalars(
                select(AddressEntity)
                .where(AddressEntity.user_id == customer_id)
                .order_by(AddressEntity.is_default.desc(), AddressEntity.created_at.asc())
            ).all()
        )
        return [AddressResponse.model_validate(x) for x in rows]

    def create_address(
        self,
        *,
        customer_id: UUID,
        payload: AddressCreateRequest,
        request_id: str | None,
    ) -> AddressResponse:
        existing_count = len(
            list(
                self.db.scalars(
                    select(AddressEntity.id).where(
                        AddressEntity.user_id == customer_id
                    )
                ).all()
            )
        )

        make_default = payload.is_default or existing_count == 0
        if make_default:
            self.db.execute(
                update(AddressEntity)
                .where(AddressEntity.user_id == customer_id)
                .values(is_default=False)
            )

        row = AddressEntity(
            user_id=customer_id,
            **payload.model_dump(exclude={"is_default"}),
            is_default=make_default,
        )
        self.db.add(row)
        self.db.flush()

        self.audit.add(
            action="customer.address.created",
            actor_user_id=customer_id,
            entity_type="address",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"is_default": make_default},
        )
        self.db.commit()
        self.db.refresh(row)
        return AddressResponse.model_validate(row)


    def update_address(
        self,
        *,
        customer_id: UUID,
        address_id: UUID,
        payload: AddressUpdateRequest,
        request_id: str | None,
    ) -> AddressResponse:
        row = self.db.get(AddressEntity, address_id)
        if row is None or row.user_id != customer_id:
            raise ApiError(404, "address_not_found", "العنوان غير موجود.")

        make_default = payload.is_default
        if make_default:
            self.db.execute(
                update(AddressEntity)
                .where(
                    AddressEntity.user_id == customer_id,
                    AddressEntity.id != address_id,
                )
                .values(is_default=False)
            )

        values = payload.model_dump(exclude={"is_default"})
        for key, value in values.items():
            setattr(row, key, value)
        if make_default:
            row.is_default = True

        self.audit.add(
            action="customer.address.updated",
            actor_user_id=customer_id,
            entity_type="address",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"is_default": row.is_default},
        )
        self.db.commit()
        self.db.refresh(row)
        return AddressResponse.model_validate(row)

    def set_default(
        self,
        *,
        customer_id: UUID,
        address_id: UUID,
        request_id: str | None,
    ) -> AddressResponse:
        row = self.db.get(AddressEntity, address_id)
        if row is None or row.user_id != customer_id:
            raise ApiError(404, "address_not_found", "العنوان غير موجود.")

        self.db.execute(
            update(AddressEntity)
            .where(AddressEntity.user_id == customer_id)
            .values(is_default=False)
        )
        row.is_default = True
        self.audit.add(
            action="customer.address.default_set",
            actor_user_id=customer_id,
            entity_type="address",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return AddressResponse.model_validate(row)

    def delete_address(
        self,
        *,
        customer_id: UUID,
        address_id: UUID,
        request_id: str | None,
    ) -> None:
        row = self.db.get(AddressEntity, address_id)
        if row is None or row.user_id != customer_id:
            raise ApiError(404, "address_not_found", "العنوان غير موجود.")

        was_default = row.is_default
        self.audit.add(
            action="customer.address.deleted",
            actor_user_id=customer_id,
            entity_type="address",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"was_default": was_default},
        )
        self.db.delete(row)
        self.db.flush()

        if was_default:
            replacement = self.db.scalar(
                select(AddressEntity)
                .where(AddressEntity.user_id == customer_id)
                .order_by(AddressEntity.created_at.asc())
                .limit(1)
            )
            if replacement is not None:
                replacement.is_default = True

        self.db.commit()

    def snapshot_for_order(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
        address_id: UUID,
        request_id: str | None,
    ) -> OrderDeliveryAddressEntity:
        order = self.db.get(OrderEntity, order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        if order.status in {
            "assigned_to_driver",
            "picked_up",
            "out_for_delivery",
            "delivered",
            "cancelled",
            "expired",
        }:
            raise ApiError(
                409,
                "delivery_address_locked",
                "لا يمكن تغيير عنوان التوصيل بعد بدء مرحلة المندوب.",
            )

        address = self.db.get(AddressEntity, address_id)
        if address is None or address.user_id != customer_id:
            raise ApiError(404, "address_not_found", "العنوان غير موجود.")

        snapshot = self.db.get(OrderDeliveryAddressEntity, order.id)
        address_change_traffic_reservation = None
        if snapshot is None or snapshot.area.strip().lower() != address.area.strip().lower():
            address_change_traffic_reservation = LaunchTrafficGovernanceService(
                self.db,
                get_settings(),
            ).admit_or_raise(
                customer_id=customer_id,
                chef_id=order.chef_id,
                service_date=order.service_date,
                area=address.area,
                request_id=request_id,
                exclude_order_id=order.id,
            )

        values = {
            "source_address_id": address.id,
            "label": address.label,
            "area": address.area,
            "street": address.street,
            "building": address.building,
            "floor": address.floor,
            "apartment": address.apartment,
            "latitude": address.latitude,
            "longitude": address.longitude,
        }

        if snapshot is None:
            snapshot = OrderDeliveryAddressEntity(
                order_id=order.id,
                **values,
            )
            self.db.add(snapshot)
        else:
            for key, value in values.items():
                setattr(snapshot, key, value)

        LaunchTrafficGovernanceService(
            self.db,
            get_settings(),
        ).attach_admitted_order(
            reservation=address_change_traffic_reservation,
            order_id=order.id,
            request_id=request_id,
        )

        self.audit.add(
            action="customer.order.delivery_address_set",
            actor_user_id=customer_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
            metadata={"address_id": str(address.id)},
        )
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot
