"""Sprint 17 Chef, Signature Menu and Today’s Kitchen.

Revision ID: 0002_sprint17
Revises: 0001_sprint16
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_sprint17"
down_revision = "0001_sprint16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dishes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("base_price_minor", sa.Integer(), nullable=False),
        sa.Column("prep_notice_hours", sa.Integer(), nullable=False),
        sa.Column("is_special_order_available", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "base_price_minor > 0",
            name="ck_dishes_positive_price",
        ),
        sa.CheckConstraint(
            "prep_notice_hours >= 0",
            name="ck_dishes_prep_notice",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chef_id",
            "name",
            name="uq_dishes_chef_name",
        ),
    )
    op.create_index("ix_dishes_chef_id", "dishes", ["chef_id"])
    op.create_index(
        "ix_dishes_chef_active",
        "dishes",
        ["chef_id", "is_active", "display_order"],
    )

    op.create_table(
        "chef_workdays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_window_start", sa.String(length=5), nullable=True),
        sa.Column("delivery_window_end", sa.String(length=5), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('open','closed')",
            name="ck_chef_workdays_status",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chef_id",
            "service_date",
            name="uq_chef_workdays_chef_service_date",
        ),
    )
    op.create_index("ix_chef_workdays_chef_id", "chef_workdays", ["chef_id"])
    op.create_index(
        "ix_workdays_date_status",
        "chef_workdays",
        ["service_date", "status"],
    )

    op.create_table(
        "daily_menu_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workday_id", sa.Uuid(), nullable=False),
        sa.Column("dish_id", sa.Uuid(), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("quantity_total", sa.Integer(), nullable=False),
        sa.Column("quantity_available", sa.Integer(), nullable=False),
        sa.Column("max_per_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "price_minor > 0",
            name="ck_daily_menu_positive_price",
        ),
        sa.CheckConstraint(
            "quantity_total >= 0",
            name="ck_daily_menu_total_quantity",
        ),
        sa.CheckConstraint(
            "quantity_available >= 0",
            name="ck_daily_menu_available_quantity",
        ),
        sa.CheckConstraint(
            "max_per_order > 0",
            name="ck_daily_menu_max_per_order",
        ),
        sa.CheckConstraint(
            "status IN ('available','sold_out','hidden')",
            name="ck_daily_menu_status",
        ),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["dishes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workday_id"],
            ["chef_workdays.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workday_id",
            "dish_id",
            name="uq_daily_menu_items_workday_dish",
        ),
    )
    op.create_index(
        "ix_daily_menu_items_dish_id",
        "daily_menu_items",
        ["dish_id"],
    )
    op.create_index(
        "ix_daily_menu_items_workday_id",
        "daily_menu_items",
        ["workday_id"],
    )
    op.create_index(
        "ix_daily_menu_workday_status",
        "daily_menu_items",
        ["workday_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_daily_menu_workday_status",
        table_name="daily_menu_items",
    )
    op.drop_index(
        "ix_daily_menu_items_workday_id",
        table_name="daily_menu_items",
    )
    op.drop_index(
        "ix_daily_menu_items_dish_id",
        table_name="daily_menu_items",
    )
    op.drop_table("daily_menu_items")

    op.drop_index("ix_workdays_date_status", table_name="chef_workdays")
    op.drop_index("ix_chef_workdays_chef_id", table_name="chef_workdays")
    op.drop_table("chef_workdays")

    op.drop_index("ix_dishes_chef_active", table_name="dishes")
    op.drop_index("ix_dishes_chef_id", table_name="dishes")
    op.drop_table("dishes")
