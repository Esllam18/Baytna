from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db_models import (
    CartEntity,
    CartItemEntity,
    ChefWorkdayEntity,
    DailyMenuItemEntity,
    DishEntity,
    InventoryReservationEntity,
    OrderEntity,
    OrderItemEntity,
    OrderStatusEventEntity,
)


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ----- Cart -----
    def active_cart(self, customer_id: UUID) -> CartEntity | None:
        return self.db.scalar(
            select(CartEntity)
            .where(
                CartEntity.customer_id == customer_id,
                CartEntity.status == "active",
            )
            .order_by(CartEntity.updated_at.desc())
            .limit(1)
        )

    def cart(self, cart_id: UUID) -> CartEntity | None:
        return self.db.get(CartEntity, cart_id)

    def create_cart(self, customer_id: UUID) -> CartEntity:
        cart = CartEntity(customer_id=customer_id, status="active")
        self.db.add(cart)
        self.db.flush()
        return cart

    def cart_items(self, cart_id: UUID) -> list[CartItemEntity]:
        return list(
            self.db.scalars(
                select(CartItemEntity)
                .where(CartItemEntity.cart_id == cart_id)
                .order_by(CartItemEntity.created_at.asc())
            ).all()
        )

    def cart_item(self, item_id: UUID) -> CartItemEntity | None:
        return self.db.get(CartItemEntity, item_id)

    def cart_item_by_menu_item(
        self,
        cart_id: UUID,
        daily_menu_item_id: UUID,
    ) -> CartItemEntity | None:
        return self.db.scalar(
            select(CartItemEntity).where(
                CartItemEntity.cart_id == cart_id,
                CartItemEntity.daily_menu_item_id == daily_menu_item_id,
            )
        )

    # ----- Menu references -----
    def daily_menu_item(self, item_id: UUID) -> DailyMenuItemEntity | None:
        return self.db.get(DailyMenuItemEntity, item_id)

    def workday(self, workday_id: UUID) -> ChefWorkdayEntity | None:
        return self.db.get(ChefWorkdayEntity, workday_id)

    def dish(self, dish_id: UUID) -> DishEntity | None:
        return self.db.get(DishEntity, dish_id)

    # ----- Inventory -----
    def reserve_inventory(
        self,
        *,
        daily_menu_item_id: UUID,
        quantity: int,
    ) -> bool:
        # Atomic decrement prevents two concurrent checkouts from overselling.
        result = self.db.execute(
            update(DailyMenuItemEntity)
            .where(
                DailyMenuItemEntity.id == daily_menu_item_id,
                DailyMenuItemEntity.status == "available",
                DailyMenuItemEntity.quantity_available >= quantity,
            )
            .values(
                quantity_available=DailyMenuItemEntity.quantity_available - quantity
            )
        )
        self.db.flush()

        if result.rowcount != 1:
            return False

        item = self.daily_menu_item(daily_menu_item_id)
        if item is not None and item.quantity_available == 0:
            item.status = "sold_out"
            self.db.flush()

        return True

    def release_inventory(
        self,
        *,
        daily_menu_item_id: UUID,
        quantity: int,
    ) -> None:
        item = self.daily_menu_item(daily_menu_item_id)
        if item is None:
            return

        item.quantity_available = min(
            item.quantity_total,
            item.quantity_available + quantity,
        )
        if item.status == "sold_out" and item.quantity_available > 0:
            item.status = "available"
        self.db.flush()

    # ----- Order aggregate -----
    def create_order(
        self,
        *,
        customer_id: UUID,
        chef_id: UUID,
        source_cart_id: UUID,
        service_date: date,
        subtotal_minor: int,
        delivery_fee_minor: int,
        discount_minor: int,
        total_minor: int,
        inventory_hold_expires_at: datetime,
    ) -> OrderEntity:
        order = OrderEntity(
            customer_id=customer_id,
            chef_id=chef_id,
            source_cart_id=source_cart_id,
            service_date=service_date,
            status="pending_payment",
            subtotal_minor=subtotal_minor,
            delivery_fee_minor=delivery_fee_minor,
            discount_minor=discount_minor,
            total_minor=total_minor,
            currency="EGP",
            inventory_hold_expires_at=inventory_hold_expires_at,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def order(self, order_id: UUID) -> OrderEntity | None:
        return self.db.get(OrderEntity, order_id)

    def orders_for_customer(self, customer_id: UUID) -> list[OrderEntity]:
        return list(
            self.db.scalars(
                select(OrderEntity)
                .where(OrderEntity.customer_id == customer_id)
                .order_by(OrderEntity.created_at.desc())
            ).all()
        )

    def order_items(self, order_id: UUID) -> list[OrderItemEntity]:
        return list(
            self.db.scalars(
                select(OrderItemEntity)
                .where(OrderItemEntity.order_id == order_id)
                .order_by(OrderItemEntity.id.asc())
            ).all()
        )

    def order_events(self, order_id: UUID) -> list[OrderStatusEventEntity]:
        return list(
            self.db.scalars(
                select(OrderStatusEventEntity)
                .where(OrderStatusEventEntity.order_id == order_id)
                .order_by(OrderStatusEventEntity.created_at.asc())
            ).all()
        )

    def active_reservations_for_order(
        self,
        order_id: UUID,
    ) -> list[InventoryReservationEntity]:
        return list(
            self.db.scalars(
                select(InventoryReservationEntity).where(
                    InventoryReservationEntity.order_id == order_id,
                    InventoryReservationEntity.status == "active",
                )
            ).all()
        )

    def expired_active_reservations(
        self,
        now: datetime,
    ) -> list[InventoryReservationEntity]:
        return list(
            self.db.scalars(
                select(InventoryReservationEntity).where(
                    InventoryReservationEntity.status == "active",
                    InventoryReservationEntity.expires_at <= now,
                )
            ).all()
        )
