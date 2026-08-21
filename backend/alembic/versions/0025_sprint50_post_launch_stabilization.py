"""Sprint 50 launch-day SLO automation and post-launch stabilization.

Revision ID: 0025_sprint50
Revises: 0024_sprint49
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_sprint50"
down_revision = "0024_sprint49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # SLO policy and auditable system rollout triggers
    # ---------------------------------------------------------------
    with op.batch_alter_table("zone_traffic_policies", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "slo_auto_pause_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch.add_column(
            sa.Column(
                "slo_consecutive_red_snapshots",
                sa.Integer(),
                nullable=False,
                server_default="2",
            )
        )
        batch.create_check_constraint(
            "ck_zone_traffic_slo_red_snapshots",
            "slo_consecutive_red_snapshots >= 2",
        )

    with op.batch_alter_table("expansion_rollout_events", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "trigger_source",
                sa.String(length=20),
                nullable=False,
                server_default="admin",
            )
        )
        batch.add_column(sa.Column("trigger_reason", sa.String(length=80), nullable=True))
        batch.add_column(
            sa.Column(
                "trigger_evidence_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.create_check_constraint(
            "ck_expansion_rollout_trigger_source",
            "trigger_source IN ('admin','system')",
        )

    # ---------------------------------------------------------------
    # Capacity forecasting: one deterministic forecast per monitor snap
    # ---------------------------------------------------------------
    op.create_table(
        "expansion_capacity_forecasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("monitoring_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("current_orders_last_hour", sa.Integer(), nullable=False),
        sa.Column("projected_orders_next_hour", sa.Float(), nullable=False),
        sa.Column("hourly_cap", sa.Integer(), nullable=True),
        sa.Column("projected_hourly_utilization_pct", sa.Float(), nullable=False),
        sa.Column("current_daily_orders", sa.Integer(), nullable=False),
        sa.Column("daily_cap", sa.Integer(), nullable=True),
        sa.Column("daily_headroom_orders", sa.Integer(), nullable=True),
        sa.Column("projected_minutes_to_daily_cap", sa.Integer(), nullable=True),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("reasons_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("horizon_minutes > 0", name="ck_capacity_forecast_horizon"),
        sa.CheckConstraint("sample_count > 0", name="ck_capacity_forecast_samples"),
        sa.CheckConstraint("projected_orders_next_hour >= 0", name="ck_capacity_forecast_orders"),
        sa.CheckConstraint("projected_hourly_utilization_pct >= 0", name="ck_capacity_forecast_util"),
        sa.CheckConstraint("risk IN ('green','amber','red')", name="ck_capacity_forecast_risk"),
        sa.ForeignKeyConstraint(["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["monitoring_snapshot_id"],
            ["expansion_monitoring_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("monitoring_snapshot_id"),
    )
    op.create_index("ix_expansion_capacity_forecasts_zone_id", "expansion_capacity_forecasts", ["zone_id"])
    op.create_index("ix_expansion_capacity_forecasts_monitoring_snapshot_id", "expansion_capacity_forecasts", ["monitoring_snapshot_id"])
    op.create_index("ix_expansion_capacity_forecasts_service_date", "expansion_capacity_forecasts", ["service_date"])
    op.create_index("ix_expansion_capacity_forecasts_risk", "expansion_capacity_forecasts", ["risk"])
    op.create_index("ix_expansion_capacity_forecasts_generated_at", "expansion_capacity_forecasts", ["generated_at"])
    op.create_index(
        "ix_capacity_forecast_zone_generated",
        "expansion_capacity_forecasts",
        ["zone_id", "generated_at"],
    )

    # ---------------------------------------------------------------
    # Daily financial close cadence reuses Sprint 49 canonical ledger
    # ---------------------------------------------------------------
    with op.batch_alter_table("daily_financial_closes", recreate="auto") as batch:
        batch.alter_column("prepared_by_admin_id", existing_type=sa.Uuid(), nullable=True)
        batch.add_column(
            sa.Column(
                "prepared_by_system",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch.add_column(sa.Column("cadence_due_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("overdue_notified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_daily_financial_closes_cadence_due_at", "daily_financial_closes", ["cadence_due_at"])

    # ---------------------------------------------------------------
    # Evidence retention metadata. Complete evidence remains permanent.
    # ---------------------------------------------------------------
    with op.batch_alter_table("launch_evidence_packs", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "retention_class",
                sa.String(length=20),
                nullable=False,
                server_default="working",
            )
        )
        batch.add_column(sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint(
            "ck_launch_evidence_pack_retention_class",
            "retention_class IN ('working','final')",
        )
    op.create_index("ix_launch_evidence_packs_retain_until", "launch_evidence_packs", ["retain_until"])
    # Existing complete Sprint 49 packs are canonical final evidence.
    op.execute(
        sa.text(
            "UPDATE launch_evidence_packs SET retention_class='final' WHERE status='complete'"
        )
    )

    # ---------------------------------------------------------------
    # Daily/idempotent post-launch expansion review
    # ---------------------------------------------------------------
    op.create_table(
        "expansion_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("monitoring_snapshots", sa.Integer(), nullable=False),
        sa.Column("red_snapshots", sa.Integer(), nullable=False),
        sa.Column("amber_snapshots", sa.Integer(), nullable=False),
        sa.Column("auto_pause_events", sa.Integer(), nullable=False),
        sa.Column("required_closes", sa.Integer(), nullable=False),
        sa.Column("closed_closes", sa.Integer(), nullable=False),
        sa.Column("overdue_closes", sa.Integer(), nullable=False),
        sa.Column("blocked_closes", sa.Integer(), nullable=False),
        sa.Column("latest_forecast_risk", sa.String(length=20), nullable=True),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("generated_by", sa.String(length=20), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('healthy','watch','blocked')", name="ck_expansion_review_status"),
        sa.CheckConstraint("recommendation IN ('continue','hold','pause')", name="ck_expansion_review_recommendation"),
        sa.CheckConstraint("generated_by IN ('admin','worker')", name="ck_expansion_review_generated_by"),
        sa.ForeignKeyConstraint(["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["launch_command_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zone_id", "review_date", name="uq_expansion_review_zone_date"),
    )
    op.create_index("ix_expansion_reviews_zone_id", "expansion_reviews", ["zone_id"])
    op.create_index("ix_expansion_reviews_session_id", "expansion_reviews", ["session_id"])
    op.create_index("ix_expansion_reviews_review_date", "expansion_reviews", ["review_date"])
    op.create_index("ix_expansion_reviews_status", "expansion_reviews", ["status"])
    op.create_index("ix_expansion_reviews_recommendation", "expansion_reviews", ["recommendation"])


def downgrade() -> None:
    op.drop_index("ix_expansion_reviews_recommendation", table_name="expansion_reviews")
    op.drop_index("ix_expansion_reviews_status", table_name="expansion_reviews")
    op.drop_index("ix_expansion_reviews_review_date", table_name="expansion_reviews")
    op.drop_index("ix_expansion_reviews_session_id", table_name="expansion_reviews")
    op.drop_index("ix_expansion_reviews_zone_id", table_name="expansion_reviews")
    op.drop_table("expansion_reviews")

    op.drop_index("ix_launch_evidence_packs_retain_until", table_name="launch_evidence_packs")
    with op.batch_alter_table("launch_evidence_packs", recreate="auto") as batch:
        batch.drop_constraint("ck_launch_evidence_pack_retention_class", type_="check")
        batch.drop_column("retain_until")
        batch.drop_column("retention_class")

    op.drop_index("ix_daily_financial_closes_cadence_due_at", table_name="daily_financial_closes")
    with op.batch_alter_table("daily_financial_closes", recreate="auto") as batch:
        batch.drop_column("overdue_notified_at")
        batch.drop_column("cadence_due_at")
        batch.drop_column("prepared_by_system")
        batch.alter_column("prepared_by_admin_id", existing_type=sa.Uuid(), nullable=False)

    op.drop_index("ix_capacity_forecast_zone_generated", table_name="expansion_capacity_forecasts")
    op.drop_index("ix_expansion_capacity_forecasts_generated_at", table_name="expansion_capacity_forecasts")
    op.drop_index("ix_expansion_capacity_forecasts_risk", table_name="expansion_capacity_forecasts")
    op.drop_index("ix_expansion_capacity_forecasts_service_date", table_name="expansion_capacity_forecasts")
    op.drop_index("ix_expansion_capacity_forecasts_monitoring_snapshot_id", table_name="expansion_capacity_forecasts")
    op.drop_index("ix_expansion_capacity_forecasts_zone_id", table_name="expansion_capacity_forecasts")
    op.drop_table("expansion_capacity_forecasts")

    with op.batch_alter_table("expansion_rollout_events", recreate="auto") as batch:
        batch.drop_constraint("ck_expansion_rollout_trigger_source", type_="check")
        batch.drop_column("trigger_evidence_json")
        batch.drop_column("trigger_reason")
        batch.drop_column("trigger_source")

    with op.batch_alter_table("zone_traffic_policies", recreate="auto") as batch:
        batch.drop_constraint("ck_zone_traffic_slo_red_snapshots", type_="check")
        batch.drop_column("slo_consecutive_red_snapshots")
        batch.drop_column("slo_auto_pause_enabled")


