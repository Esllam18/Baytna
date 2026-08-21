"""Sprint 18 Cart, Inventory Reservation and Order Aggregate.

Revision ID: 0003_sprint18
Revises: 0002_sprint17
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_sprint18"
down_revision = "0002_sprint17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','converted','abandoned')",
            name="ck_carts_status",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_carts_customer_id", "carts", ["customer_id"])
    op.create_index("ix_carts_chef_id", "carts", ["chef_id"])
    op.create_index(
        "ix_carts_customer_status",
        "carts",
        ["customer_id", "status"],
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cart_id", sa.Uuid(), nullable=False),
        sa.Column("daily_menu_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_cart_items_quantity",
        ),
        sa.CheckConstraint(
            "unit_price_minor > 0",
            name="ck_cart_items_unit_price",
        ),
        sa.ForeignKeyConstraint(
            ["cart_id"],
            ["carts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["daily_menu_item_id"],
            ["daily_menu_items.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cart_id",
            "daily_menu_item_id",
            name="uq_cart_items_cart_menu_item",
        ),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.create_index(
        "ix_cart_items_daily_menu_item_id",
        "cart_items",
        ["daily_menu_item_id"],
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("source_cart_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("subtotal_minor", sa.Integer(), nullable=False),
        sa.Column("delivery_fee_minor", sa.Integer(), nullable=False),
        sa.Column("discount_minor", sa.Integer(), nullable=False),
        sa.Column("total_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "inventory_hold_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending_payment','confirmed','cancelled','expired')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint(
            "subtotal_minor >= 0",
            name="ck_orders_subtotal",
        ),
        sa.CheckConstraint(
            "delivery_fee_minor >= 0",
            name="ck_orders_delivery_fee",
        ),
        sa.CheckConstraint(
            "discount_minor >= 0",
            name="ck_orders_discount",
        ),
        sa.CheckConstraint(
            "total_minor >= 0",
            name="ck_orders_total",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_cart_id"],
            ["carts.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_cart_id"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_chef_id", "orders", ["chef_id"])
    op.create_index(
        "ix_orders_customer_created",
        "orders",
        ["customer_id", "created_at"],
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("daily_menu_item_id", sa.Uuid(), nullable=False),
        sa.Column("dish_id", sa.Uuid(), nullable=False),
        sa.Column("dish_name", sa.String(length=140), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total_minor", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity",
        ),
        sa.CheckConstraint(
            "unit_price_minor > 0",
            name="ck_order_items_unit_price",
        ),
        sa.CheckConstraint(
            "line_total_minor > 0",
            name="ck_order_items_line_total",
        ),
        sa.ForeignKeyConstraint(
            ["daily_menu_item_id"],
            ["daily_menu_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["dishes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("daily_menu_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_inventory_reservations_quantity",
        ),
        sa.CheckConstraint(
            "status IN ('active','released','converted','expired')",
            name="ck_inventory_reservations_status",
        ),
        sa.ForeignKeyConstraint(
            ["daily_menu_item_id"],
            ["daily_menu_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_id",
            "daily_menu_item_id",
            name="uq_inventory_reservations_order_item",
        ),
    )
    op.create_index(
        "ix_inventory_reservations_order_id",
        "inventory_reservations",
        ["order_id"],
    )
    op.create_index(
        "ix_inventory_reservations_daily_menu_item_id",
        "inventory_reservations",
        ["daily_menu_item_id"],
    )
    op.create_index(
        "ix_inventory_reservations_status_expiry",
        "inventory_reservations",
        ["status", "expires_at"],
    )

    op.create_table(
        "order_status_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_status_events_order_id",
        "order_status_events",
        ["order_id"],
    )
    op.create_index(
        "ix_order_status_events_order_created",
        "order_status_events",
        ["order_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_status_events_order_created",
        table_name="order_status_events",
    )
    op.drop_index(
        "ix_order_status_events_order_id",
        table_name="order_status_events",
    )
    op.drop_table("order_status_events")

    op.drop_index(
        "ix_inventory_reservations_status_expiry",
        table_name="inventory_reservations",
    )
    op.drop_index(
        "ix_inventory_reservations_daily_menu_item_id",
        table_name="inventory_reservations",
    )
    op.drop_index(
        "ix_inventory_reservations_order_id",
        table_name="inventory_reservations",
    )
    op.drop_table("inventory_reservations")

    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("ix_orders_customer_created", table_name="orders")
    op.drop_index("ix_orders_chef_id", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")

    op.drop_index(
        "ix_cart_items_daily_menu_item_id",
        table_name="cart_items",
    )
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")
    op.drop_table("cart_items")

    op.drop_index("ix_carts_customer_status", table_name="carts")
    op.drop_index("ix_carts_chef_id", table_name="carts")
    op.drop_index("ix_carts_customer_id", table_name="carts")
    op.drop_table("carts")
