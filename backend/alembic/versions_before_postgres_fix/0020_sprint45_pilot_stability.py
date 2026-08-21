"""Sprint 45 pilot execution, stability tracking and QA evidence.

Revision ID: 0020_sprint45
Revises: 0019_sprint44
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_sprint45"
down_revision = "0019_sprint44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_programs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("required_stability_weeks", sa.Integer(), nullable=False),
        sa.Column("rating_target", sa.Float(), nullable=False),
        sa.Column("repeat_customer_target_pct", sa.Float(), nullable=False),
        sa.Column("on_time_target_pct", sa.Float(), nullable=False),
        sa.Column("cancellation_max_pct", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned','active','completed','archived')",
            name="ck_pilot_programs_status",
        ),
        sa.CheckConstraint(
            "required_stability_weeks BETWEEN 8 AND 26",
            name="ck_pilot_programs_stability_weeks",
        ),
        sa.CheckConstraint(
            "rating_target BETWEEN 1 AND 5",
            name="ck_pilot_programs_rating_target",
        ),
        sa.CheckConstraint(
            "repeat_customer_target_pct BETWEEN 0 AND 100",
            name="ck_pilot_programs_repeat_target",
        ),
        sa.CheckConstraint(
            "on_time_target_pct BETWEEN 0 AND 100",
            name="ck_pilot_programs_on_time_target",
        ),
        sa.CheckConstraint(
            "cancellation_max_pct BETWEEN 0 AND 100",
            name="ck_pilot_programs_cancellation_target",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pilot_programs_status",
        "pilot_programs",
        ["status"],
    )

    op.create_table(
        "pilot_weekly_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("week_index", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("is_full_week", sa.Boolean(), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column("orders_created", sa.Integer(), nullable=False),
        sa.Column("delivered_orders", sa.Integer(), nullable=False),
        sa.Column("cancelled_orders", sa.Integer(), nullable=False),
        sa.Column("cancellation_rate_pct", sa.Float(), nullable=False),
        sa.Column("unique_customers", sa.Integer(), nullable=False),
        sa.Column("repeat_customers", sa.Integer(), nullable=False),
        sa.Column("repeat_customer_rate_pct", sa.Float(), nullable=False),
        sa.Column("average_chef_rating", sa.Float(), nullable=True),
        sa.Column("reviews_count", sa.Integer(), nullable=False),
        sa.Column("on_time_delivery_rate_pct", sa.Float(), nullable=True),
        sa.Column("on_time_measurable_deliveries", sa.Integer(), nullable=False),
        sa.Column("late_deliveries", sa.Integer(), nullable=False),
        sa.Column("delivery_promise_coverage_pct", sa.Float(), nullable=False),
        sa.Column("gmv_minor", sa.Integer(), nullable=False),
        sa.Column("captured_minor", sa.Integer(), nullable=False),
        sa.Column("refunded_minor", sa.Integer(), nullable=False),
        sa.Column("net_collected_minor", sa.Integer(), nullable=False),
        sa.Column("support_tickets", sa.Integer(), nullable=False),
        sa.Column("refund_count", sa.Integer(), nullable=False),
        sa.Column("refund_rate_pct", sa.Float(), nullable=False),
        sa.Column("rating_met", sa.Boolean(), nullable=True),
        sa.Column("repeat_met", sa.Boolean(), nullable=True),
        sa.Column("on_time_met", sa.Boolean(), nullable=True),
        sa.Column("cancellation_met", sa.Boolean(), nullable=True),
        sa.Column("week_evaluable", sa.Boolean(), nullable=False),
        sa.Column("week_passed", sa.Boolean(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("week_index > 0", name="ck_pilot_weekly_week_index"),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["pilot_programs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_id",
            "week_index",
            name="uq_pilot_weekly_program_week",
        ),
    )
    op.create_index(
        "ix_pilot_weekly_snapshots_program_id",
        "pilot_weekly_snapshots",
        ["program_id"],
    )
    op.create_index(
        "ix_pilot_weekly_program_range",
        "pilot_weekly_snapshots",
        ["program_id", "week_start"],
    )

    op.create_table(
        "pilot_qa_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reference", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','passed','failed','not_applicable')",
            name="ck_pilot_qa_status",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["pilot_programs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_id",
            "evidence_type",
            name="uq_pilot_qa_program_type",
        ),
    )
    op.create_index(
        "ix_pilot_qa_evidence_program_id",
        "pilot_qa_evidence",
        ["program_id"],
    )
    op.create_index(
        "ix_pilot_qa_program_status",
        "pilot_qa_evidence",
        ["program_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pilot_qa_program_status",
        table_name="pilot_qa_evidence",
    )
    op.drop_index(
        "ix_pilot_qa_evidence_program_id",
        table_name="pilot_qa_evidence",
    )
    op.drop_table("pilot_qa_evidence")

    op.drop_index(
        "ix_pilot_weekly_program_range",
        table_name="pilot_weekly_snapshots",
    )
    op.drop_index(
        "ix_pilot_weekly_snapshots_program_id",
        table_name="pilot_weekly_snapshots",
    )
    op.drop_table("pilot_weekly_snapshots")

    op.drop_index(
        "ix_pilot_programs_status",
        table_name="pilot_programs",
    )
    op.drop_table("pilot_programs")
