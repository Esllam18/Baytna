"""Sprint 26 Special Orders, Scheduling and Preorders.

Revision ID: 0011_sprint26
Revises: 0010_sprint25
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_sprint26"
down_revision = "0010_sprint25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders", recreate="auto") as batch_op:
        batch_op.alter_column(
            "source_cart_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "order_type",
                sa.String(length=20),
                nullable=False,
                server_default="standard",
            )
        )
        batch_op.create_check_constraint(
            "ck_orders_order_type",
            "order_type IN ('standard','special')",
        )

    with op.batch_alter_table("order_items", recreate="auto") as batch_op:
        batch_op.alter_column(
            "daily_menu_item_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )

    op.create_table(
        "chef_weekly_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("delivery_window_start", sa.String(length=5), nullable=True),
        sa.Column("delivery_window_end", sa.String(length=5), nullable=True),
        sa.Column("max_special_orders", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "weekday BETWEEN 0 AND 6",
            name="ck_chef_weekly_schedule_weekday",
        ),
        sa.CheckConstraint(
            "max_special_orders >= 0",
            name="ck_chef_weekly_schedule_capacity",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chef_id",
            "weekday",
            name="uq_chef_weekly_schedule_day",
        ),
    )
    op.create_index(
        "ix_chef_weekly_schedules_chef_id",
        "chef_weekly_schedules",
        ["chef_id"],
    )
    op.create_index(
        "ix_chef_weekly_schedule_lookup",
        "chef_weekly_schedules",
        ["chef_id", "weekday"],
    )

    op.create_table(
        "chef_schedule_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("delivery_window_start", sa.String(length=5), nullable=True),
        sa.Column("delivery_window_end", sa.String(length=5), nullable=True),
        sa.Column("max_special_orders", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "max_special_orders IS NULL OR max_special_orders >= 0",
            name="ck_chef_schedule_override_capacity",
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
            name="uq_chef_schedule_override_date",
        ),
    )
    op.create_index(
        "ix_chef_schedule_overrides_chef_id",
        "chef_schedule_overrides",
        ["chef_id"],
    )
    op.create_index(
        "ix_chef_schedule_override_lookup",
        "chef_schedule_overrides",
        ["chef_id", "service_date"],
    )

    op.create_table(
        "special_order_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("dish_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("request_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("requested_service_date", sa.Date(), nullable=False),
        sa.Column("requested_window_start", sa.String(length=5), nullable=True),
        sa.Column("requested_window_end", sa.String(length=5), nullable=True),
        sa.Column("requested_unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("customer_note", sa.Text(), nullable=True),
        sa.Column("proposed_service_date", sa.Date(), nullable=True),
        sa.Column("proposed_window_start", sa.String(length=5), nullable=True),
        sa.Column("proposed_window_end", sa.String(length=5), nullable=True),
        sa.Column("proposed_unit_price_minor", sa.Integer(), nullable=True),
        sa.Column("final_service_date", sa.Date(), nullable=True),
        sa.Column("final_window_start", sa.String(length=5), nullable=True),
        sa.Column("final_window_end", sa.String(length=5), nullable=True),
        sa.Column("final_unit_price_minor", sa.Integer(), nullable=True),
        sa.Column("final_total_minor", sa.Integer(), nullable=True),
        sa.Column("chef_note", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=240), nullable=True),
        sa.Column("offer_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chef_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "request_type IN ('special','preorder')",
            name="ck_special_order_request_type",
        ),
        sa.CheckConstraint(
            "status IN ('chef_review','counter_offer','awaiting_payment','scheduled','rejected','cancelled','expired')",
            name="ck_special_order_status",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_special_order_quantity"),
        sa.CheckConstraint(
            "requested_unit_price_minor > 0",
            name="ck_special_order_requested_price",
        ),
        sa.CheckConstraint(
            "proposed_unit_price_minor IS NULL OR proposed_unit_price_minor > 0",
            name="ck_special_order_proposed_price",
        ),
        sa.CheckConstraint(
            "final_unit_price_minor IS NULL OR final_unit_price_minor > 0",
            name="ck_special_order_final_price",
        ),
        sa.CheckConstraint(
            "final_total_minor IS NULL OR final_total_minor > 0",
            name="ck_special_order_final_total",
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
            ["dish_id"],
            ["dishes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index(
        "ix_special_order_requests_customer_id",
        "special_order_requests",
        ["customer_id"],
    )
    op.create_index(
        "ix_special_order_requests_chef_id",
        "special_order_requests",
        ["chef_id"],
    )
    op.create_index(
        "ix_special_order_requests_dish_id",
        "special_order_requests",
        ["dish_id"],
    )
    op.create_index(
        "ix_special_order_requests_order_id",
        "special_order_requests",
        ["order_id"],
    )
    op.create_index(
        "ix_special_orders_customer_status",
        "special_order_requests",
        ["customer_id", "status", "created_at"],
    )
    op.create_index(
        "ix_special_orders_chef_status_date",
        "special_order_requests",
        ["chef_id", "status", "requested_service_date"],
    )

    op.create_table(
        "special_order_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("special_order_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=240), nullable=True),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["special_order_id"],
            ["special_order_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_special_order_events_special_order_id",
        "special_order_events",
        ["special_order_id"],
    )
    op.create_index(
        "ix_special_order_events_request_created",
        "special_order_events",
        ["special_order_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_special_order_events_request_created",
        table_name="special_order_events",
    )
    op.drop_index(
        "ix_special_order_events_special_order_id",
        table_name="special_order_events",
    )
    op.drop_table("special_order_events")

    op.drop_index(
        "ix_special_orders_chef_status_date",
        table_name="special_order_requests",
    )
    op.drop_index(
        "ix_special_orders_customer_status",
        table_name="special_order_requests",
    )
    op.drop_index(
        "ix_special_order_requests_order_id",
        table_name="special_order_requests",
    )
    op.drop_index(
        "ix_special_order_requests_dish_id",
        table_name="special_order_requests",
    )
    op.drop_index(
        "ix_special_order_requests_chef_id",
        table_name="special_order_requests",
    )
    op.drop_index(
        "ix_special_order_requests_customer_id",
        table_name="special_order_requests",
    )
    op.drop_table("special_order_requests")

    op.drop_index(
        "ix_chef_schedule_override_lookup",
        table_name="chef_schedule_overrides",
    )
    op.drop_index(
        "ix_chef_schedule_overrides_chef_id",
        table_name="chef_schedule_overrides",
    )
    op.drop_table("chef_schedule_overrides")

    op.drop_index(
        "ix_chef_weekly_schedule_lookup",
        table_name="chef_weekly_schedules",
    )
    op.drop_index(
        "ix_chef_weekly_schedules_chef_id",
        table_name="chef_weekly_schedules",
    )
    op.drop_table("chef_weekly_schedules")

    with op.batch_alter_table("order_items", recreate="auto") as batch_op:
        batch_op.alter_column(
            "daily_menu_item_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )

    with op.batch_alter_table("orders", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_orders_order_type", type_="check")
        batch_op.drop_column("order_type")
        batch_op.alter_column(
            "source_cart_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )

