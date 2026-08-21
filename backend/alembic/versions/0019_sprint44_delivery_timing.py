"""Sprint 44 promised delivery windows and timing outcome.

Revision ID: 0019_sprint44
Revises: 0018_sprint43
"""
from alembic import op
import sqlalchemy as sa


revision = "0019_sprint44"
down_revision = "0018_sprint43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(
            sa.Column(
                "promised_delivery_window_start_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "promised_delivery_window_end_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "promised_delivery_timezone",
                sa.String(length=80),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "delivery_promise_source",
                sa.String(length=40),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "delivery_promise_snapshot_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    op.create_index(
        "ix_orders_promised_delivery_window_end_at",
        "orders",
        ["promised_delivery_window_end_at"],
    )
    op.create_index(
        "ix_orders_delivery_promise_deadline",
        "orders",
        ["status", "promised_delivery_window_end_at"],
    )

    with op.batch_alter_table("delivery_tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "delivery_timing_status",
                sa.String(length=20),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "late_by_minutes",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.create_check_constraint(
            "ck_delivery_tasks_timing_status",
            "delivery_timing_status IS NULL OR "
            "delivery_timing_status IN ('on_time','late','unmeasurable')",
        )
        batch_op.create_check_constraint(
            "ck_delivery_tasks_late_by_minutes",
            "late_by_minutes IS NULL OR late_by_minutes >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("delivery_tasks", recreate="auto") as batch_op:
        batch_op.drop_constraint(
            "ck_delivery_tasks_late_by_minutes",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_delivery_tasks_timing_status",
            type_="check",
        )
        batch_op.drop_column("late_by_minutes")
        batch_op.drop_column("delivery_timing_status")

    op.drop_index(
        "ix_orders_delivery_promise_deadline",
        table_name="orders",
    )
    op.drop_index(
        "ix_orders_promised_delivery_window_end_at",
        table_name="orders",
    )

    with op.batch_alter_table("orders", recreate="auto") as batch_op:
        batch_op.drop_column("delivery_promise_snapshot_at")
        batch_op.drop_column("delivery_promise_source")
        batch_op.drop_column("promised_delivery_timezone")
        batch_op.drop_column("promised_delivery_window_end_at")
        batch_op.drop_column("promised_delivery_window_start_at")

