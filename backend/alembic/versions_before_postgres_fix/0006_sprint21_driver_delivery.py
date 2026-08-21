"""Sprint 21 Driver Dispatch, Pickup and Delivery Workflow.

Revision ID: 0006_sprint21
Revises: 0005_sprint20
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_sprint21"
down_revision = "0005_sprint20"
branch_labels = None
depends_on = None


NEW_ORDER_STATUS_CHECK = (
    "status IN ("
    "'pending_payment',"
    "'confirmed',"
    "'accepted_by_chef',"
    "'preparing',"
    "'ready_for_pickup',"
    "'assigned_to_driver',"
    "'picked_up',"
    "'out_for_delivery',"
    "'delivered',"
    "'cancelled',"
    "'expired'"
    ")"
)

OLD_ORDER_STATUS_CHECK = (
    "status IN ("
    "'pending_payment',"
    "'confirmed',"
    "'accepted_by_chef',"
    "'preparing',"
    "'ready_for_pickup',"
    "'cancelled',"
    "'expired'"
    ")"
)


def upgrade() -> None:
    with op.batch_alter_table("orders", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_orders_status", type_="check")
        batch_op.create_check_constraint(
            "ck_orders_status",
            NEW_ORDER_STATUS_CHECK,
        )

    op.create_table(
        "order_delivery_addresses",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("source_address_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(length=80), nullable=True),
        sa.Column("area", sa.String(length=120), nullable=False),
        sa.Column("street", sa.String(length=200), nullable=True),
        sa.Column("building", sa.String(length=80), nullable=True),
        sa.Column("floor", sa.String(length=40), nullable=True),
        sa.Column("apartment", sa.String(length=40), nullable=True),
        sa.Column("latitude", sa.String(length=32), nullable=True),
        sa.Column("longitude", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_address_id"],
            ["addresses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("order_id"),
    )

    op.create_table(
        "delivery_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_pickup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("route_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_proof_type", sa.String(length=30), nullable=True),
        sa.Column(
            "delivery_proof_reference",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column("issue_from_status", sa.String(length=30), nullable=True),
        sa.Column("issue_code", sa.String(length=80), nullable=True),
        sa.Column("issue_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('unassigned','to_pickup','at_pickup','picked_up','to_customer','delivered','delivery_issue','cancelled')",
            name="ck_delivery_tasks_status",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.user_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_delivery_tasks_order_id", "delivery_tasks", ["order_id"])
    op.create_index("ix_delivery_tasks_chef_id", "delivery_tasks", ["chef_id"])
    op.create_index("ix_delivery_tasks_driver_id", "delivery_tasks", ["driver_id"])
    op.create_index(
        "ix_delivery_tasks_open",
        "delivery_tasks",
        ["status", "driver_id", "created_at"],
    )
    op.create_index(
        "ix_delivery_tasks_driver_status",
        "delivery_tasks",
        ["driver_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_delivery_tasks_driver_status",
        table_name="delivery_tasks",
    )
    op.drop_index(
        "ix_delivery_tasks_open",
        table_name="delivery_tasks",
    )
    op.drop_index("ix_delivery_tasks_driver_id", table_name="delivery_tasks")
    op.drop_index("ix_delivery_tasks_chef_id", table_name="delivery_tasks")
    op.drop_index("ix_delivery_tasks_order_id", table_name="delivery_tasks")
    op.drop_table("delivery_tasks")

    op.drop_table("order_delivery_addresses")

    with op.batch_alter_table("orders", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_orders_status", type_="check")
        batch_op.create_check_constraint(
            "ck_orders_status",
            OLD_ORDER_STATUS_CHECK,
        )
