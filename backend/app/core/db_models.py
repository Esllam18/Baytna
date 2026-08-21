from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserEntity(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    customer_profile: Mapped["CustomerProfileEntity | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CustomerProfileEntity(Base):
    __tablename__ = "customer_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="ar")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    user: Mapped[UserEntity] = relationship(back_populates="customer_profile")


class ChefProfileEntity(Base):
    __tablename__ = "chef_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    area: Mapped[str] = mapped_column(String(120), nullable=False, default="6 أكتوبر")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="application_draft"
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_open_today: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DriverProfileEntity(Base):
    __tablename__ = "driver_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="offline")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AddressEntity(Base):
    __tablename__ = "addresses"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(80))
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    street: Mapped[str | None] = mapped_column(String(200))
    building: Mapped[str | None] = mapped_column(String(80))
    floor: Mapped[str | None] = mapped_column(String(40))
    apartment: Mapped[str | None] = mapped_column(String(40))
    latitude: Mapped[str | None] = mapped_column(String(32))
    longitude: Mapped[str | None] = mapped_column(String(32))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class OtpChallengeEntity(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AuthSessionEntity(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_session_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AuditLogEntity(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    request_id: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )


Index(
    "ix_audit_logs_entity",
    AuditLogEntity.entity_type,
    AuditLogEntity.entity_id,
)



class DishEntity(Base):
    __tablename__ = "dishes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="أطباق رئيسية")
    base_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    prep_notice_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    is_special_order_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    media_asset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("base_price_minor > 0", name="ck_dishes_positive_price"),
        CheckConstraint("prep_notice_hours >= 0", name="ck_dishes_prep_notice"),
        UniqueConstraint("chef_id", "name", name="uq_dishes_chef_name"),
    )


class ChefWorkdayEntity(Base):
    __tablename__ = "chef_workdays"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_window_start: Mapped[str | None] = mapped_column(String(5))
    delivery_window_end: Mapped[str | None] = mapped_column(String(5))
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "chef_id",
            "service_date",
            name="uq_chef_workdays_chef_service_date",
        ),
        CheckConstraint(
            "status IN ('open','closed')",
            name="ck_chef_workdays_status",
        ),
    )


class DailyMenuItemEntity(Base):
    __tablename__ = "daily_menu_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workday_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_workdays.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dish_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dishes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_total: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_order: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "workday_id",
            "dish_id",
            name="uq_daily_menu_items_workday_dish",
        ),
        CheckConstraint("price_minor > 0", name="ck_daily_menu_positive_price"),
        CheckConstraint("quantity_total >= 0", name="ck_daily_menu_total_quantity"),
        CheckConstraint(
            "quantity_available >= 0",
            name="ck_daily_menu_available_quantity",
        ),
        CheckConstraint("max_per_order > 0", name="ck_daily_menu_max_per_order"),
        CheckConstraint(
            "status IN ('available','sold_out','hidden')",
            name="ck_daily_menu_status",
        ),
    )


Index(
    "ix_dishes_chef_active",
    DishEntity.chef_id,
    DishEntity.is_active,
    DishEntity.display_order,
)

Index(
    "ix_workdays_date_status",
    ChefWorkdayEntity.service_date,
    ChefWorkdayEntity.status,
)

Index(
    "ix_daily_menu_workday_status",
    DailyMenuItemEntity.workday_id,
    DailyMenuItemEntity.status,
)



class CartEntity(Base):
    __tablename__ = "carts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chef_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','converted','abandoned')",
            name="ck_carts_status",
        ),
    )


class CartItemEntity(Base):
    __tablename__ = "cart_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    cart_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    daily_menu_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_menu_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "daily_menu_item_id",
            name="uq_cart_items_cart_menu_item",
        ),
        CheckConstraint("quantity > 0", name="ck_cart_items_quantity"),
        CheckConstraint(
            "unit_price_minor > 0",
            name="ck_cart_items_unit_price",
        ),
    )


class OrderEntity(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_cart_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("carts.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    order_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="standard",
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending_payment",
    )
    subtotal_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EGP")
    inventory_hold_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    promised_delivery_window_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    promised_delivery_window_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    promised_delivery_timezone: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )
    delivery_promise_source: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )
    delivery_promise_snapshot_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_payment','confirmed','accepted_by_chef','preparing','ready_for_pickup','assigned_to_driver','picked_up','out_for_delivery','delivered','cancelled','expired')",
            name="ck_orders_status",
        ),
        CheckConstraint(
            "order_type IN ('standard','special')",
            name="ck_orders_order_type",
        ),
        CheckConstraint("subtotal_minor >= 0", name="ck_orders_subtotal"),
        CheckConstraint("delivery_fee_minor >= 0", name="ck_orders_delivery_fee"),
        CheckConstraint("discount_minor >= 0", name="ck_orders_discount"),
        CheckConstraint("total_minor >= 0", name="ck_orders_total"),
    )


class OrderItemEntity(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    daily_menu_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_menu_items.id", ondelete="RESTRICT"),
        nullable=True,
    )
    dish_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dishes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dish_name: Mapped[str] = mapped_column(String(140), nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity"),
        CheckConstraint(
            "unit_price_minor > 0",
            name="ck_order_items_unit_price",
        ),
        CheckConstraint(
            "line_total_minor > 0",
            name="ck_order_items_line_total",
        ),
    )


class InventoryReservationEntity(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    daily_menu_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_menu_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "daily_menu_item_id",
            name="uq_inventory_reservations_order_item",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_inventory_reservations_quantity",
        ),
        CheckConstraint(
            "status IN ('active','released','converted','expired')",
            name="ck_inventory_reservations_status",
        ),
    )


class OrderStatusEventEntity(Base):
    __tablename__ = "order_status_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


Index(
    "ix_carts_customer_status",
    CartEntity.customer_id,
    CartEntity.status,
)

Index(
    "ix_orders_customer_created",
    OrderEntity.customer_id,
    OrderEntity.created_at,
)

Index(
    "ix_orders_delivery_promise_deadline",
    OrderEntity.status,
    OrderEntity.promised_delivery_window_end_at,
)

Index(
    "ix_inventory_reservations_status_expiry",
    InventoryReservationEntity.status,
    InventoryReservationEntity.expires_at,
)

Index(
    "ix_order_status_events_order_created",
    OrderStatusEventEntity.order_id,
    OrderStatusEventEntity.created_at,
)



class PaymentEntity(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_order_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    provider_transaction_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    provider_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    refunded_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EGP")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    checkout_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_payments_amount"),
        CheckConstraint("refunded_minor >= 0", name="ck_payments_refunded"),
        CheckConstraint(
            "status IN ('pending','succeeded','failed','cancelled','expired')",
            name="ck_payments_status",
        ),
    )


class PaymentWebhookEventEntity(Base):
    __tablename__ = "payment_webhook_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="received"
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_payment_webhook_provider_event",
        ),
        CheckConstraint(
            "processing_status IN ('received','processed','ignored','failed')",
            name="ck_payment_webhook_processing_status",
        ),
    )


class RefundEntity(Base):
    __tablename__ = "refunds"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    provider_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "payment_id",
            "idempotency_key",
            name="uq_refunds_payment_idempotency",
        ),
        CheckConstraint("amount_minor > 0", name="ck_refunds_amount"),
        CheckConstraint(
            "status IN ('pending','succeeded','failed')",
            name="ck_refunds_status",
        ),
    )


Index(
    "ix_payments_order_status",
    PaymentEntity.order_id,
    PaymentEntity.status,
)

Index(
    "ix_payment_webhooks_reference",
    PaymentWebhookEventEntity.provider,
    PaymentWebhookEventEntity.provider_reference,
)

Index(
    "ix_refunds_order_status",
    RefundEntity.order_id,
    RefundEntity.status,
)



class PaymentProviderTransactionEntity(Base):
    __tablename__ = "payment_provider_transactions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_transaction_id: Mapped[str] = mapped_column(String(180), nullable=False)
    payment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_order_reference: Mapped[str | None] = mapped_column(String(180))
    parent_provider_transaction_id: Mapped[str | None] = mapped_column(String(180))
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False, default="payment")
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refunded_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_transaction_id",
            name="uq_payment_provider_transaction",
        ),
        CheckConstraint(
            "transaction_type IN ('payment','refund','void')",
            name="ck_payment_provider_transaction_type",
        ),
        CheckConstraint(
            "amount_minor >= 0",
            name="ck_payment_provider_transaction_amount",
        ),
        CheckConstraint(
            "refunded_minor >= 0",
            name="ck_payment_provider_transaction_refunded",
        ),
    )


class PaymentReconciliationIssueEntity(Base):
    __tablename__ = "payment_reconciliation_issues"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    fingerprint: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    payment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider_transaction_id: Mapped[str | None] = mapped_column(String(180))
    issue_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    expected_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    actual_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "issue_type IN ('unmatched_provider_transaction','amount_mismatch','currency_mismatch','status_mismatch','refund_mismatch')",
            name="ck_payment_reconciliation_issue_type",
        ),
        CheckConstraint(
            "status IN ('open','resolved')",
            name="ck_payment_reconciliation_issue_status",
        ),
    )


Index(
    "ix_payment_provider_tx_payment",
    PaymentProviderTransactionEntity.payment_id,
    PaymentProviderTransactionEntity.observed_at,
)

Index(
    "ix_payment_provider_tx_order_ref",
    PaymentProviderTransactionEntity.provider,
    PaymentProviderTransactionEntity.provider_order_reference,
)

Index(
    "ix_payment_reconciliation_open",
    PaymentReconciliationIssueEntity.status,
    PaymentReconciliationIssueEntity.issue_type,
    PaymentReconciliationIssueEntity.last_detected_at,
)



class ChefOrderFulfillmentEntity(Base):
    __tablename__ = "chef_order_fulfillments"

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="new",
    )
    acceptance_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    estimated_ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preparation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    packaging_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    chef_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "stage IN ('new','accepted','preparing','packaging','ready','rejected')",
            name="ck_chef_order_fulfillment_stage",
        ),
    )


Index(
    "ix_chef_fulfillment_queue",
    ChefOrderFulfillmentEntity.chef_id,
    ChefOrderFulfillmentEntity.stage,
    ChefOrderFulfillmentEntity.acceptance_deadline_at,
)



class OrderDeliveryAddressEntity(Base):
    __tablename__ = "order_delivery_addresses"

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_address_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str | None] = mapped_column(String(80))
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    street: Mapped[str | None] = mapped_column(String(200))
    building: Mapped[str | None] = mapped_column(String(80))
    floor: Mapped[str | None] = mapped_column(String(40))
    apartment: Mapped[str | None] = mapped_column(String(40))
    latitude: Mapped[str | None] = mapped_column(String(32))
    longitude: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class DeliveryTaskEntity(Base):
    __tablename__ = "delivery_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("driver_profiles.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unassigned",
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrived_pickup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    route_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_timing_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    late_by_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    delivery_proof_type: Mapped[str | None] = mapped_column(String(30))
    delivery_proof_reference: Mapped[str | None] = mapped_column(String(500))
    delivery_proof_media_asset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issue_from_status: Mapped[str | None] = mapped_column(String(30))
    issue_code: Mapped[str | None] = mapped_column(String(80))
    issue_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('unassigned','to_pickup','at_pickup','picked_up','to_customer','delivered','delivery_issue','cancelled')",
            name="ck_delivery_tasks_status",
        ),
        CheckConstraint(
            "delivery_timing_status IS NULL OR delivery_timing_status IN ('on_time','late','unmeasurable')",
            name="ck_delivery_tasks_timing_status",
        ),
        CheckConstraint(
            "late_by_minutes IS NULL OR late_by_minutes >= 0",
            name="ck_delivery_tasks_late_by_minutes",
        ),
    )


Index(
    "ix_delivery_tasks_open",
    DeliveryTaskEntity.status,
    DeliveryTaskEntity.driver_id,
    DeliveryTaskEntity.created_at,
)

Index(
    "ix_delivery_tasks_driver_status",
    DeliveryTaskEntity.driver_id,
    DeliveryTaskEntity.status,
)



class ReviewEntity(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("driver_profiles.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    food_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    packaging: Mapped[int] = mapped_column(Integer, nullable=False)
    order_accuracy: Mapped[int] = mapped_column(Integer, nullable=False)
    value_for_money: Mapped[int] = mapped_column(Integer, nullable=False)
    chef_overall: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    moderation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("food_quality BETWEEN 1 AND 5", name="ck_reviews_food_quality"),
        CheckConstraint("packaging BETWEEN 1 AND 5", name="ck_reviews_packaging"),
        CheckConstraint(
            "order_accuracy BETWEEN 1 AND 5",
            name="ck_reviews_order_accuracy",
        ),
        CheckConstraint(
            "value_for_money BETWEEN 1 AND 5",
            name="ck_reviews_value_for_money",
        ),
        CheckConstraint("chef_overall BETWEEN 1 AND 5", name="ck_reviews_chef_overall"),
        CheckConstraint(
            "delivery_overall IS NULL OR delivery_overall BETWEEN 1 AND 5",
            name="ck_reviews_delivery_overall",
        ),
    )


class SupportTicketEntity(Base):
    __tablename__ = "support_tickets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new")

    resolution_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('food_quality','missing_item','wrong_item','late_delivery','delivery_issue','refund','payment','app_issue','other')",
            name="ck_support_tickets_category",
        ),
        CheckConstraint(
            "priority IN ('normal','high','urgent')",
            name="ck_support_tickets_priority",
        ),
        CheckConstraint(
            "status IN ('new','assigned','investigating','awaiting_customer','awaiting_internal','resolved','closed')",
            name="ck_support_tickets_status",
        ),
    )


class SupportMessageEntity(Base):
    __tablename__ = "support_messages"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "sender_role IN ('customer','admin','system')",
            name="ck_support_messages_sender_role",
        ),
    )


Index(
    "ix_reviews_chef_visible",
    ReviewEntity.chef_id,
    ReviewEntity.is_visible,
    ReviewEntity.created_at,
)

Index(
    "ix_support_customer_status",
    SupportTicketEntity.customer_id,
    SupportTicketEntity.status,
    SupportTicketEntity.created_at,
)

Index(
    "ix_support_admin_status",
    SupportTicketEntity.assigned_admin_id,
    SupportTicketEntity.status,
    SupportTicketEntity.created_at,
)



class FavoriteChefEntity(Base):
    __tablename__ = "favorite_chefs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "chef_id",
            name="uq_favorite_chefs_customer_chef",
        ),
    )


class FavoriteDishEntity(Base):
    __tablename__ = "favorite_dishes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dish_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dishes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "dish_id",
            name="uq_favorite_dishes_customer_dish",
        ),
    )


class NotificationEntity(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "dedupe_key",
            name="uq_notifications_user_dedupe_key",
        ),
    )


class LoyaltyAccountEntity(Base):
    __tablename__ = "loyalty_accounts"

    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    balance_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_earned_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    lifetime_redeemed_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("balance_points >= 0", name="ck_loyalty_balance_nonnegative"),
        CheckConstraint(
            "lifetime_earned_points >= 0",
            name="ck_loyalty_earned_nonnegative",
        ),
        CheckConstraint(
            "lifetime_redeemed_points >= 0",
            name="ck_loyalty_redeemed_nonnegative",
        ),
    )


class LoyaltyTransactionEntity(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("loyalty_accounts.customer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    source_order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('earn_order','redeem','adjustment')",
            name="ck_loyalty_transaction_type",
        ),
        CheckConstraint("points != 0", name="ck_loyalty_points_nonzero"),
    )


Index(
    "ix_favorite_chefs_customer_created",
    FavoriteChefEntity.customer_id,
    FavoriteChefEntity.created_at,
)

Index(
    "ix_favorite_dishes_customer_created",
    FavoriteDishEntity.customer_id,
    FavoriteDishEntity.created_at,
)

Index(
    "ix_notifications_user_unread",
    NotificationEntity.user_id,
    NotificationEntity.read_at,
    NotificationEntity.created_at,
)

Index(
    "ix_loyalty_transactions_customer_created",
    LoyaltyTransactionEntity.customer_id,
    LoyaltyTransactionEntity.created_at,
)



class CouponEntity(Base):
    __tablename__ = "coupons"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    min_subtotal_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_discount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_customer_usage_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reserved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redeemed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stack_with_subscription: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("discount_type IN ('fixed','percent')", name="ck_coupons_discount_type"),
        CheckConstraint("discount_value > 0", name="ck_coupons_discount_value"),
        CheckConstraint("min_subtotal_minor >= 0", name="ck_coupons_min_subtotal"),
        CheckConstraint("max_discount_minor IS NULL OR max_discount_minor > 0", name="ck_coupons_max_discount"),
        CheckConstraint("total_usage_limit IS NULL OR total_usage_limit > 0", name="ck_coupons_total_limit"),
        CheckConstraint("per_customer_usage_limit > 0", name="ck_coupons_customer_limit"),
        CheckConstraint("reserved_count >= 0", name="ck_coupons_reserved_nonnegative"),
        CheckConstraint("redeemed_count >= 0", name="ck_coupons_redeemed_nonnegative"),
    )


class CouponRedemptionEntity(Base):
    __tablename__ = "coupon_redemptions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coupon_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reserved")
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        CheckConstraint("discount_minor > 0", name="ck_coupon_redemptions_discount"),
        CheckConstraint("status IN ('reserved','applied','released')", name="ck_coupon_redemptions_status"),
    )


class LoyaltyRedemptionEntity(Base):
    __tablename__ = "loyalty_redemptions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("loyalty_accounts.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reserved")
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        CheckConstraint("points > 0", name="ck_loyalty_redemptions_points"),
        CheckConstraint("discount_minor > 0", name="ck_loyalty_redemptions_discount"),
        CheckConstraint("status IN ('reserved','applied','released')", name="ck_loyalty_redemptions_status"),
    )


class SubscriptionPlanEntity(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    order_discount_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_order_discount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loyalty_multiplier_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="ck_subscription_plans_price"),
        CheckConstraint("duration_days > 0", name="ck_subscription_plans_duration"),
        CheckConstraint("order_discount_bps BETWEEN 0 AND 10000", name="ck_subscription_plans_order_discount"),
        CheckConstraint("max_order_discount_minor IS NULL OR max_order_discount_minor > 0", name="ck_subscription_plans_max_discount"),
        CheckConstraint("loyalty_multiplier_bps >= 10000", name="ck_subscription_plans_loyalty_multiplier"),
    )


class CustomerSubscriptionEntity(Base):
    __tablename__ = "customer_subscriptions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("status IN ('active','cancelled','expired')", name="ck_customer_subscriptions_status"),
        CheckConstraint("source IN ('manual','promo','billing')", name="ck_customer_subscriptions_source"),
    )


class OrderPricingAdjustmentEntity(Base):
    __tablename__ = "order_pricing_adjustments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    adjustment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("order_id", "adjustment_type", name="uq_order_pricing_adjustment_type"),
        CheckConstraint("adjustment_type IN ('coupon','loyalty','subscription')", name="ck_order_pricing_adjustment_type"),
        CheckConstraint("amount_minor >= 0", name="ck_order_pricing_adjustment_amount"),
    )


Index("ix_coupon_redemptions_coupon_status", CouponRedemptionEntity.coupon_id, CouponRedemptionEntity.status)
Index("ix_coupon_redemptions_customer_coupon", CouponRedemptionEntity.customer_id, CouponRedemptionEntity.coupon_id)
Index("ix_loyalty_redemptions_customer_status", LoyaltyRedemptionEntity.customer_id, LoyaltyRedemptionEntity.status)
Index("ix_customer_subscriptions_customer_status", CustomerSubscriptionEntity.customer_id, CustomerSubscriptionEntity.status, CustomerSubscriptionEntity.ends_at)
Index("ix_order_pricing_adjustments_order", OrderPricingAdjustmentEntity.order_id, OrderPricingAdjustmentEntity.created_at)



class AdminOrderNoteEntity(Base):
    __tablename__ = "admin_order_notes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    admin_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


Index(
    "ix_admin_order_notes_order_created",
    AdminOrderNoteEntity.order_id,
    AdminOrderNoteEntity.created_at,
)

Index("ix_orders_status_created_reporting", OrderEntity.status, OrderEntity.created_at)
Index("ix_payments_status_created_reporting", PaymentEntity.status, PaymentEntity.created_at)
Index("ix_refunds_status_created_reporting", RefundEntity.status, RefundEntity.created_at)
Index("ix_support_status_created_reporting", SupportTicketEntity.status, SupportTicketEntity.created_at)
Index("ix_delivery_status_created_reporting", DeliveryTaskEntity.status, DeliveryTaskEntity.created_at)


class ChefWeeklyScheduleEntity(Base):
    __tablename__ = "chef_weekly_schedules"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    delivery_window_start: Mapped[str | None] = mapped_column(String(5))
    delivery_window_end: Mapped[str | None] = mapped_column(String(5))
    max_special_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("chef_id", "weekday", name="uq_chef_weekly_schedule_day"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_chef_weekly_schedule_weekday"),
        CheckConstraint("max_special_orders >= 0", name="ck_chef_weekly_schedule_capacity"),
    )


class ChefScheduleOverrideEntity(Base):
    __tablename__ = "chef_schedule_overrides"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    delivery_window_start: Mapped[str | None] = mapped_column(String(5))
    delivery_window_end: Mapped[str | None] = mapped_column(String(5))
    max_special_orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("chef_id", "service_date", name="uq_chef_schedule_override_date"),
        CheckConstraint("max_special_orders IS NULL OR max_special_orders >= 0", name="ck_chef_schedule_override_capacity"),
    )


class SpecialOrderRequestEntity(Base):
    __tablename__ = "special_order_requests"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    chef_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    dish_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dishes.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False, default="special")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="chef_review")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_service_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_window_start: Mapped[str | None] = mapped_column(String(5))
    requested_window_end: Mapped[str | None] = mapped_column(String(5))
    requested_unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_note: Mapped[str | None] = mapped_column(Text)
    proposed_service_date: Mapped[date | None] = mapped_column(Date)
    proposed_window_start: Mapped[str | None] = mapped_column(String(5))
    proposed_window_end: Mapped[str | None] = mapped_column(String(5))
    proposed_unit_price_minor: Mapped[int | None] = mapped_column(Integer)
    final_service_date: Mapped[date | None] = mapped_column(Date)
    final_window_start: Mapped[str | None] = mapped_column(String(5))
    final_window_end: Mapped[str | None] = mapped_column(String(5))
    final_unit_price_minor: Mapped[int | None] = mapped_column(Integer)
    final_total_minor: Mapped[int | None] = mapped_column(Integer)
    chef_note: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(String(240))
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    chef_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("request_type IN ('special','preorder')", name="ck_special_order_request_type"),
        CheckConstraint("status IN ('chef_review','counter_offer','awaiting_payment','scheduled','rejected','cancelled','expired')", name="ck_special_order_status"),
        CheckConstraint("quantity > 0", name="ck_special_order_quantity"),
        CheckConstraint("requested_unit_price_minor > 0", name="ck_special_order_requested_price"),
        CheckConstraint("proposed_unit_price_minor IS NULL OR proposed_unit_price_minor > 0", name="ck_special_order_proposed_price"),
        CheckConstraint("final_unit_price_minor IS NULL OR final_unit_price_minor > 0", name="ck_special_order_final_price"),
        CheckConstraint("final_total_minor IS NULL OR final_total_minor > 0", name="ck_special_order_final_total"),
    )


class SpecialOrderEventEntity(Base):
    __tablename__ = "special_order_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    special_order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("special_order_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(240))
    data_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


Index("ix_chef_weekly_schedule_lookup", ChefWeeklyScheduleEntity.chef_id, ChefWeeklyScheduleEntity.weekday)
Index("ix_chef_schedule_override_lookup", ChefScheduleOverrideEntity.chef_id, ChefScheduleOverrideEntity.service_date)
Index("ix_special_orders_customer_status", SpecialOrderRequestEntity.customer_id, SpecialOrderRequestEntity.status, SpecialOrderRequestEntity.created_at)
Index("ix_special_orders_chef_status_date", SpecialOrderRequestEntity.chef_id, SpecialOrderRequestEntity.status, SpecialOrderRequestEntity.requested_service_date)
Index("ix_special_order_events_request_created", SpecialOrderEventEntity.special_order_id, SpecialOrderEventEntity.created_at)


class OutboxEventEntity(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processing','retry','published','dead_letter')",
            name="ck_outbox_events_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_outbox_events_attempts"),
        CheckConstraint("max_attempts > 0", name="ck_outbox_events_max_attempts"),
    )


class BackgroundJobEntity(Base):
    __tablename__ = "background_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','retry','succeeded','dead_letter','cancelled')",
            name="ck_background_jobs_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_background_jobs_attempts"),
        CheckConstraint("max_attempts > 0", name="ck_background_jobs_max_attempts"),
    )


class WorkerHeartbeatEntity(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    processed_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','idle','error','stopped')",
            name="ck_worker_heartbeats_status",
        ),
    )


Index(
    "ix_outbox_due",
    OutboxEventEntity.status,
    OutboxEventEntity.available_at,
    OutboxEventEntity.created_at,
)

Index(
    "ix_outbox_aggregate",
    OutboxEventEntity.aggregate_type,
    OutboxEventEntity.aggregate_id,
    OutboxEventEntity.created_at,
)

Index(
    "ix_background_jobs_due",
    BackgroundJobEntity.status,
    BackgroundJobEntity.available_at,
    BackgroundJobEntity.created_at,
)





class OperationsIncidentEntity(Base):
    __tablename__ = "operations_incidents"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(220),
        nullable=False,
        unique=True,
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSON,
        nullable=False,
        default=dict,
    )
    owner_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    acknowledged_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    resolved_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('chef_sla','delivery_sla','support_sla','payment','reliability','notifications','traffic')",
            name="ck_operations_incidents_category",
        ),
        CheckConstraint(
            "severity IN ('info','warning','high','critical')",
            name="ck_operations_incidents_severity",
        ),
        CheckConstraint(
            "status IN ('open','acknowledged','resolved')",
            name="ck_operations_incidents_status",
        ),
    )


Index(
    "ix_operations_incidents_active",
    OperationsIncidentEntity.status,
    OperationsIncidentEntity.severity,
    OperationsIncidentEntity.last_detected_at,
)






class ProviderCostImportBatchEntity(Base):
    __tablename__ = "provider_cost_import_batches"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pilot_program_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_to_egp: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    external_reference: Mapped[str] = mapped_column(String(180), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_source_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_egp_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applied_cost_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_errors_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    assigned_reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_flags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    applied_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("provider", "external_reference", name="uq_provider_cost_import_reference"),
        CheckConstraint("status IN ('draft','validated','applied','failed')", name="ck_provider_cost_import_status"),
        CheckConstraint(
            "review_status IN ('pending','assigned','approved','rejected')",
            name="ck_provider_cost_import_review_status",
        ),
        CheckConstraint("rows_count >= 0", name="ck_provider_cost_import_rows"),
        CheckConstraint("total_source_minor >= 0", name="ck_provider_cost_import_source_total"),
        CheckConstraint("total_egp_minor >= 0", name="ck_provider_cost_import_egp_total"),
    )


class ProviderCostImportLineEntity(Base):
    __tablename__ = "provider_cost_import_lines"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("provider_cost_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_key: Mapped[str] = mapped_column(String(180), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    incurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    cost_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    egp_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(220), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    applied_cost_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("economics_cost_entries.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("batch_id", "line_key", name="uq_provider_cost_import_line_key"),
        CheckConstraint("source_amount_minor > 0", name="ck_provider_cost_import_line_source_amount"),
        CheckConstraint("egp_amount_minor > 0", name="ck_provider_cost_import_line_egp_amount"),
    )


class ProviderSettlementBatchEntity(Base):
    __tablename__ = "provider_settlement_batches"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pilot_program_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pilot_programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(180), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mismatched_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gross_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fees_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refunds_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_settlement_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    operations_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )
    assigned_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    close_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reconciled_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("provider", "external_reference", name="uq_provider_settlement_reference"),
        CheckConstraint("status IN ('draft','reconciled','blocked')", name="ck_provider_settlement_status"),
        CheckConstraint(
            "operations_status IN ('open','review','closed','reopened')",
            name="ck_provider_settlement_operations_status",
        ),
        CheckConstraint("rows_count >= 0", name="ck_provider_settlement_rows"),
        CheckConstraint("fees_minor >= 0", name="ck_provider_settlement_fees"),
        CheckConstraint("refunds_minor >= 0", name="ck_provider_settlement_refunds"),
    )


class ProviderSettlementLineEntity(Base):
    __tablename__ = "provider_settlement_lines"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("provider_settlement_batches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    provider_transaction_id: Mapped[str] = mapped_column(String(180), nullable=False)
    settlement_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    gross_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refund_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_settlement_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matched_payment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    reconciliation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    issues_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    applied_cost_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("economics_cost_entries.id", ondelete="SET NULL"), nullable=True
    )
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("batch_id", "provider_transaction_id", name="uq_provider_settlement_line_tx"),
        CheckConstraint("gross_amount_minor >= 0", name="ck_provider_settlement_gross"),
        CheckConstraint("fee_minor >= 0", name="ck_provider_settlement_fee"),
        CheckConstraint("refund_minor >= 0", name="ck_provider_settlement_refund"),
        CheckConstraint("reconciliation_status IN ('pending','matched','mismatch','unmatched')", name="ck_provider_settlement_line_status"),
    )


class ExpansionZoneBudgetEntity(Base):
    __tablename__ = "expansion_zone_budgets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expansion_zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    allocated_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    committed_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spent_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EGP")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("zone_id", "category", name="uq_expansion_zone_budget_category"),
        CheckConstraint("allocated_minor > 0", name="ck_expansion_budget_allocated"),
        CheckConstraint("committed_minor >= 0", name="ck_expansion_budget_committed"),
        CheckConstraint("spent_minor >= 0", name="ck_expansion_budget_spent"),
        CheckConstraint("currency = 'EGP'", name="ck_expansion_budget_currency"),
        CheckConstraint("committed_minor + spent_minor <= allocated_minor", name="ck_expansion_budget_not_overspent"),
    )


class ExpansionRolloutEventEntity(Base):
    __tablename__ = "expansion_rollout_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expansion_zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_order_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expansion_assessments.id", ondelete="SET NULL"), nullable=True
    )
    budget_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    triggered_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False, default="admin")
    trigger_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trigger_evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("rollout_percent BETWEEN 0 AND 100", name="ck_expansion_rollout_percent"),
        CheckConstraint("from_stage IN ('not_started','canary','limited','full','paused')", name="ck_expansion_rollout_from_stage"),
        CheckConstraint("to_stage IN ('not_started','canary','limited','full','paused')", name="ck_expansion_rollout_to_stage"),
        CheckConstraint("trigger_source IN ('admin','system')", name="ck_expansion_rollout_trigger_source"),
    )


class EconomicsCostEntryEntity(Base):
    __tablename__ = "economics_cost_entries"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    pilot_program_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    area: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    incurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cost_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    cost_scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EGP")
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    external_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_economics_cost_amount"),
        CheckConstraint("currency = 'EGP'", name="ck_economics_cost_currency"),
        CheckConstraint(
            "cost_scope IN ('variable','fixed')",
            name="ck_economics_cost_scope",
        ),
        CheckConstraint(
            "cost_type IN ('chef_payout','delivery_partner','payment_processing','packaging','refund_fee','customer_recovery','other_variable','fixed_operations','communications_provider','cloud_storage','cloud_infrastructure','provider_adjustment')",
            name="ck_economics_cost_type",
        ),
        CheckConstraint(
            "source IN ('manual','provider','import')",
            name="ck_economics_cost_source",
        ),
    )


Index(
    "ix_economics_cost_program_date",
    EconomicsCostEntryEntity.pilot_program_id,
    EconomicsCostEntryEntity.incurred_on,
)
Index(
    "ix_economics_cost_order_type",
    EconomicsCostEntryEntity.order_id,
    EconomicsCostEntryEntity.cost_type,
)


class ExpansionZoneEntity(Base):
    __tablename__ = "expansion_zones"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    area: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    source_program_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="candidate", index=True
    )
    min_delivered_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    min_contribution_margin_pct: Mapped[float] = mapped_column(Float, nullable=False, default=15.0)
    min_operational_profit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rollout_stage: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started", index=True
    )
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_order_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rollout_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rollout_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate','ready','approved','live','paused','rejected')",
            name="ck_expansion_zone_status",
        ),
        CheckConstraint(
            "min_delivered_orders > 0",
            name="ck_expansion_zone_min_orders",
        ),
        CheckConstraint(
            "min_contribution_margin_pct BETWEEN -100 AND 100",
            name="ck_expansion_zone_margin",
        ),
        CheckConstraint(
            "rollout_stage IN ('not_started','canary','limited','full','paused')",
            name="ck_expansion_zone_rollout_stage",
        ),
        CheckConstraint(
            "rollout_percent BETWEEN 0 AND 100",
            name="ck_expansion_zone_rollout_percent",
        ),
    )



class ZoneTrafficPolicyEntity(Base):
    __tablename__ = "zone_traffic_policies"

    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hourly_order_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chef_daily_order_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enforce_rollout_bucket: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    warning_utilization_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0
    )
    critical_utilization_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=95.0
    )
    rejection_spike_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=30.0
    )
    rejection_spike_min_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    slo_auto_pause_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    slo_consecutive_red_snapshots: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "hourly_order_cap IS NULL OR hourly_order_cap > 0",
            name="ck_zone_traffic_hourly_cap",
        ),
        CheckConstraint(
            "chef_daily_order_cap IS NULL OR chef_daily_order_cap > 0",
            name="ck_zone_traffic_chef_daily_cap",
        ),
        CheckConstraint(
            "warning_utilization_pct > 0 AND warning_utilization_pct <= 100",
            name="ck_zone_traffic_warning_pct",
        ),
        CheckConstraint(
            "critical_utilization_pct > 0 AND critical_utilization_pct <= 100",
            name="ck_zone_traffic_critical_pct",
        ),
        CheckConstraint(
            "rejection_spike_pct > 0 AND rejection_spike_pct <= 100",
            name="ck_zone_traffic_rejection_pct",
        ),
        CheckConstraint(
            "rejection_spike_min_attempts > 0",
            name="ck_zone_traffic_rejection_attempts",
        ),
        CheckConstraint(
            "slo_consecutive_red_snapshots >= 2",
            name="ck_zone_traffic_slo_red_snapshots",
        ),
    )


class ZoneAdmissionEventEntity(Base):
    __tablename__ = "zone_admission_events"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    chef_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chef_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    rollout_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    rollout_bucket: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_usage_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hourly_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hourly_usage_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chef_daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chef_usage_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('admitted','rejected')",
            name="ck_zone_admission_decision",
        ),
        CheckConstraint(
            "rollout_percent BETWEEN 0 AND 100",
            name="ck_zone_admission_rollout_percent",
        ),
        CheckConstraint(
            "rollout_bucket IS NULL OR rollout_bucket BETWEEN 0 AND 99",
            name="ck_zone_admission_rollout_bucket",
        ),
    )


Index(
    "ix_zone_admission_zone_created",
    ZoneAdmissionEventEntity.zone_id,
    ZoneAdmissionEventEntity.created_at,
)
Index(
    "ix_zone_admission_zone_service_decision",
    ZoneAdmissionEventEntity.zone_id,
    ZoneAdmissionEventEntity.service_date,
    ZoneAdmissionEventEntity.decision,
)


class ExpansionMonitoringSnapshotEntity(Base):
    __tablename__ = "expansion_monitoring_snapshots"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rollout_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admitted_orders_today: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_utilization_pct: Mapped[float] = mapped_column(Float, nullable=False)
    hourly_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admitted_orders_last_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    hourly_utilization_pct: Mapped[float] = mapped_column(Float, nullable=False)
    admission_attempts_last_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    admission_rejections_last_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    rejection_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    available_drivers: Mapped[int] = mapped_column(Integer, nullable=False)
    open_chefs: Mapped[int] = mapped_column(Integer, nullable=False)
    top_chef_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    chef_daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_chef_utilization_pct: Mapped[float] = mapped_column(Float, nullable=False)
    health: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="worker")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "health IN ('green','amber','red')",
            name="ck_expansion_monitoring_health",
        ),
        CheckConstraint(
            "daily_utilization_pct >= 0",
            name="ck_expansion_monitoring_daily_util",
        ),
        CheckConstraint(
            "hourly_utilization_pct >= 0",
            name="ck_expansion_monitoring_hourly_util",
        ),
        CheckConstraint(
            "rejection_rate_pct BETWEEN 0 AND 100",
            name="ck_expansion_monitoring_reject_rate",
        ),
    )


Index(
    "ix_expansion_monitoring_zone_observed",
    ExpansionMonitoringSnapshotEntity.zone_id,
    ExpansionMonitoringSnapshotEntity.observed_at,
)


class ExpansionCapacityForecastEntity(Base):
    __tablename__ = "expansion_capacity_forecasts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monitoring_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_monitoring_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    current_orders_last_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    projected_orders_next_hour: Mapped[float] = mapped_column(Float, nullable=False)
    hourly_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_hourly_utilization_pct: Mapped[float] = mapped_column(Float, nullable=False)
    current_daily_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_headroom_orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_minutes_to_daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reasons_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    __table_args__ = (
        CheckConstraint("horizon_minutes > 0", name="ck_capacity_forecast_horizon"),
        CheckConstraint("sample_count > 0", name="ck_capacity_forecast_samples"),
        CheckConstraint("projected_orders_next_hour >= 0", name="ck_capacity_forecast_orders"),
        CheckConstraint("projected_hourly_utilization_pct >= 0", name="ck_capacity_forecast_util"),
        CheckConstraint("risk IN ('green','amber','red')", name="ck_capacity_forecast_risk"),
    )


Index(
    "ix_capacity_forecast_zone_generated",
    ExpansionCapacityForecastEntity.zone_id,
    ExpansionCapacityForecastEntity.generated_at,
)


class LaunchCommandSessionEntity(Base):
    __tablename__ = "launch_command_sessions"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    pilot_program_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    launch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned", index=True
    )
    incident_commander_admin_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    finance_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    operations_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_admin_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aborted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('planned','active','paused','completed','aborted')",
            name="ck_launch_command_session_status",
        ),
    )


Index(
    "ix_launch_command_zone_status",
    LaunchCommandSessionEntity.zone_id,
    LaunchCommandSessionEntity.status,
)


class LaunchRunbookStepEntity(Base):
    __tablename__ = "launch_runbook_steps"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("launch_command_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_key: Mapped[str] = mapped_column(String(80), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    evidence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("session_id", "step_key", name="uq_launch_runbook_step_key"),
        CheckConstraint("sequence > 0", name="ck_launch_runbook_sequence"),
        CheckConstraint(
            "status IN ('pending','passed','failed','skipped')",
            name="ck_launch_runbook_status",
        ),
    )


class LaunchCommandEventEntity(Base):
    __tablename__ = "launch_command_events"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("launch_command_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    actor_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info','warning','high','critical')",
            name="ck_launch_command_event_severity",
        ),
    )


class LaunchTrafficOverrideEntity(Base):
    __tablename__ = "launch_traffic_overrides"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("launch_command_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    override_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    previous_value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    override_value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    activated_by_admin_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reverted_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "override_type IN ('daily_order_cap','hourly_order_cap','chef_daily_order_cap','admission_enabled')",
            name="ck_launch_traffic_override_type",
        ),
        CheckConstraint(
            "status IN ('active','reverted','expired')",
            name="ck_launch_traffic_override_status",
        ),
    )


Index(
    "ix_launch_override_zone_status",
    LaunchTrafficOverrideEntity.zone_id,
    LaunchTrafficOverrideEntity.status,
)


class DailyFinancialCloseEntity(Base):
    __tablename__ = "daily_financial_closes"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("launch_command_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pilot_program_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    close_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    delivered_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_payment_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    captured_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refunded_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_collected_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contribution_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    operational_profit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cost_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unverified_cost_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_provider_imports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unclosed_settlements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_payment_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prepared_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    prepared_by_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cadence_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    overdue_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reopened_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    prepared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("session_id", "close_date", name="uq_daily_financial_close_session_date"),
        CheckConstraint(
            "status IN ('draft','ready','blocked','closed','reopened')",
            name="ck_daily_financial_close_status",
        ),
        CheckConstraint(
            "revenue_coverage_pct BETWEEN 0 AND 100",
            name="ck_daily_close_revenue_coverage",
        ),
        CheckConstraint(
            "cost_coverage_pct BETWEEN 0 AND 100",
            name="ck_daily_close_cost_coverage",
        ),
    )


class LaunchRollbackDrillEntity(Base):
    __tablename__ = "launch_rollback_drills"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("launch_command_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running", index=True
    )
    target_recovery_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    recovery_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pre_state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_by_admin_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    verified_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "mode IN ('tabletop','live_controlled')",
            name="ck_launch_rollback_drill_mode",
        ),
        CheckConstraint(
            "status IN ('running','passed','failed','aborted')",
            name="ck_launch_rollback_drill_status",
        ),
        CheckConstraint(
            "target_recovery_seconds > 0",
            name="ck_launch_rollback_target",
        ),
    )


class LaunchEvidencePackEntity(Base):
    __tablename__ = "launch_evidence_packs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("launch_command_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    release_version: Mapped[str] = mapped_column(String(30), nullable=False)
    migration_head: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_class: Mapped[str] = mapped_column(String(20), nullable=False, default="working")
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    generated_by_admin_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('complete','incomplete')",
            name="ck_launch_evidence_pack_status",
        ),
        CheckConstraint(
            "retention_class IN ('working','final')",
            name="ck_launch_evidence_pack_retention_class",
        ),
    )


Index(
    "ix_launch_evidence_session_generated",
    LaunchEvidencePackEntity.session_id,
    LaunchEvidencePackEntity.generated_at,
)


class ExpansionReviewEntity(Base):
    __tablename__ = "expansion_reviews"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expansion_zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("launch_command_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    monitoring_snapshots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    red_snapshots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amber_snapshots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_pause_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required_closes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_closes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overdue_closes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_closes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_forecast_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="worker")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("zone_id", "review_date", name="uq_expansion_review_zone_date"),
        CheckConstraint("status IN ('healthy','watch','blocked')", name="ck_expansion_review_status"),
        CheckConstraint("recommendation IN ('continue','hold','pause')", name="ck_expansion_review_recommendation"),
        CheckConstraint("generated_by IN ('admin','worker')", name="ck_expansion_review_generated_by"),
    )


class ExpansionAssessmentEntity(Base):
    __tablename__ = "expansion_assessments"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    zone_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("expansion_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    delivered_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    net_collected_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    variable_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    contribution_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    contribution_margin_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    fixed_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    operational_profit_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    revenue_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    unverified_cost_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    economics_evaluable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    stability_gate_met: Mapped[bool] = mapped_column(Boolean, nullable=False)
    post_pilot_scale_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    generated_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('ready','blocked')",
            name="ck_expansion_assessment_decision",
        ),
        CheckConstraint(
            "cost_coverage_pct BETWEEN 0 AND 100",
            name="ck_expansion_assessment_cost_coverage",
        ),
        CheckConstraint(
            "revenue_coverage_pct BETWEEN 0 AND 100",
            name="ck_expansion_assessment_revenue_coverage",
        ),
    )


Index(
    "ix_expansion_assessment_zone_generated",
    ExpansionAssessmentEntity.zone_id,
    ExpansionAssessmentEntity.generated_at,
)


class PilotProgramEntity(Base):
    __tablename__ = "pilot_programs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planned",
        index=True,
    )
    required_stability_weeks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=8,
    )
    rating_target: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=4.7,
    )
    repeat_customer_target_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=40.0,
    )
    on_time_target_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=95.0,
    )
    cancellation_max_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('planned','active','completed','archived')",
            name="ck_pilot_programs_status",
        ),
        CheckConstraint(
            "required_stability_weeks BETWEEN 8 AND 26",
            name="ck_pilot_programs_stability_weeks",
        ),
        CheckConstraint(
            "rating_target BETWEEN 1 AND 5",
            name="ck_pilot_programs_rating_target",
        ),
        CheckConstraint(
            "repeat_customer_target_pct BETWEEN 0 AND 100",
            name="ck_pilot_programs_repeat_target",
        ),
        CheckConstraint(
            "on_time_target_pct BETWEEN 0 AND 100",
            name="ck_pilot_programs_on_time_target",
        ),
        CheckConstraint(
            "cancellation_max_pct BETWEEN 0 AND 100",
            name="ck_pilot_programs_cancellation_target",
        ),
    )


class PilotWeeklySnapshotEntity(Base):
    __tablename__ = "pilot_weekly_snapshots"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    program_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_index: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    is_full_week: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)

    orders_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancellation_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repeat_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repeat_customer_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_chef_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    on_time_delivery_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_time_measurable_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_promise_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gmv_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    captured_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refunded_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_collected_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_tickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refund_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refund_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    rating_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    repeat_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    on_time_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cancellation_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    week_evaluable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    week_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "week_index",
            name="uq_pilot_weekly_program_week",
        ),
        CheckConstraint(
            "week_index > 0",
            name="ck_pilot_weekly_week_index",
        ),
    )


class PilotQaEvidenceEntity(Base):
    __tablename__ = "pilot_qa_evidence"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    program_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pilot_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "evidence_type",
            name="uq_pilot_qa_program_type",
        ),
        CheckConstraint(
            "status IN ('pending','passed','failed','not_applicable')",
            name="ck_pilot_qa_status",
        ),
    )


Index(
    "ix_pilot_weekly_program_range",
    PilotWeeklySnapshotEntity.program_id,
    PilotWeeklySnapshotEntity.week_start,
)

Index(
    "ix_pilot_qa_program_status",
    PilotQaEvidenceEntity.program_id,
    PilotQaEvidenceEntity.status,
)


class RateLimitBucketEntity(Base):
    __tablename__ = "rate_limit_buckets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "scope",
            "key_hash",
            "window_start",
            name="uq_rate_limit_scope_key_window",
        ),
        CheckConstraint(
            "window_seconds > 0",
            name="ck_rate_limit_window_positive",
        ),
        CheckConstraint(
            "request_count >= 0",
            name="ck_rate_limit_count_nonnegative",
        ),
    )


class SecurityEventEntity(Base):
    __tablename__ = "security_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_security_event_severity",
        ),
    )


Index(
    "ix_rate_limit_expiry",
    RateLimitBucketEntity.expires_at,
)

Index(
    "ix_rate_limit_scope_window",
    RateLimitBucketEntity.scope,
    RateLimitBucketEntity.window_start,
)

Index(
    "ix_security_events_created",
    SecurityEventEntity.created_at,
)

Index(
    "ix_security_events_type_created",
    SecurityEventEntity.event_type,
    SecurityEventEntity.created_at,
)



class MediaAssetEntity(Base):
    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    storage_provider: Mapped[str] = mapped_column(String(30), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    expected_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    upload_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "purpose IN ('chef_avatar','dish_image','support_attachment','delivery_proof','customer_attachment','other')",
            name="ck_media_assets_purpose",
        ),
        CheckConstraint(
            "visibility IN ('private','public')",
            name="ck_media_assets_visibility",
        ),
        CheckConstraint(
            "status IN ('pending','ready','failed','deleted')",
            name="ck_media_assets_status",
        ),
        CheckConstraint(
            "expected_size_bytes > 0",
            name="ck_media_assets_expected_size",
        ),
        CheckConstraint(
            "actual_size_bytes IS NULL OR actual_size_bytes >= 0",
            name="ck_media_assets_actual_size",
        ),
    )


class PushDeviceEntity(Base):
    __tablename__ = "push_devices"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(120))
    app_version: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            "platform IN ('ios','android','web')",
            name="ck_push_devices_platform",
        ),
    )


class NotificationPreferenceEntity(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    support_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marketing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class NotificationDeliveryEntity(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    provider_status: Mapped[str | None] = mapped_column(String(40))
    provider_error_code: Mapped[str | None] = mapped_column(String(120))
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "channel",
            "target_ref",
            name="uq_notification_delivery_target",
        ),
        CheckConstraint(
            "channel IN ('push','sms')",
            name="ck_notification_delivery_channel",
        ),
        CheckConstraint(
            "status IN ('pending','processing','retry','succeeded','dead_letter','skipped')",
            name="ck_notification_delivery_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_notification_delivery_attempts",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_notification_delivery_max_attempts",
        ),
    )


Index(
    "ix_media_owner_status",
    MediaAssetEntity.owner_user_id,
    MediaAssetEntity.status,
    MediaAssetEntity.created_at,
)

Index(
    "ix_push_devices_user_active",
    PushDeviceEntity.user_id,
    PushDeviceEntity.is_active,
    PushDeviceEntity.updated_at,
)

Index(
    "ix_notification_deliveries_due",
    NotificationDeliveryEntity.status,
    NotificationDeliveryEntity.available_at,
    NotificationDeliveryEntity.created_at,
)

Index(
    "ix_notification_deliveries_user_status",
    NotificationDeliveryEntity.user_id,
    NotificationDeliveryEntity.status,
    NotificationDeliveryEntity.created_at,
)


class SupportMessageAttachmentEntity(Base):
    __tablename__ = "support_message_attachments"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("support_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    media_asset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (UniqueConstraint("message_id", "media_asset_id", name="uq_support_message_attachment"),)


class NotificationTemplateEntity(Base):
    __tablename__ = "notification_templates"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title_template: Mapped[str] = mapped_column(String(180), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class NotificationProviderEventEntity(Base):
    __tablename__ = "notification_provider_events"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    event_status: Mapped[str] = mapped_column(String(30), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matched_delivery_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("notification_deliveries.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_notification_provider_event"),
        CheckConstraint("channel IN ('push','sms')", name="ck_notification_provider_event_channel"),
        CheckConstraint("event_status IN ('accepted','delivered','failed','bounced')", name="ck_notification_provider_event_status"),
    )

Index("ix_support_message_attachments_message", SupportMessageAttachmentEntity.message_id, SupportMessageAttachmentEntity.created_at)
Index("ix_provider_events_unprocessed", NotificationProviderEventEntity.processed_at, NotificationProviderEventEntity.created_at)
