"""Sprint 48 launch traffic governance and vendor accounting operations.

Revision ID: 0023_sprint48
Revises: 0022_sprint47
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_sprint48"
down_revision = "0022_sprint47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # Provider import review queue / maker-checker state
    # ---------------------------------------------------------------
    with op.batch_alter_table("provider_cost_import_batches", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "review_status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            )
        )
        batch.add_column(sa.Column("assigned_reviewer_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("review_note", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column(
                "risk_flags_json",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_provider_cost_import_assigned_reviewer",
            "users",
            ["assigned_reviewer_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_provider_cost_import_reviewed_by",
            "users",
            ["reviewed_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint(
            "ck_provider_cost_import_review_status",
            "review_status IN ('pending','assigned','approved','rejected')",
        )
    op.create_index(
        "ix_provider_cost_import_batches_review_status",
        "provider_cost_import_batches",
        ["review_status"],
    )
    op.execute(
        sa.text(
            """
            UPDATE provider_cost_import_batches
            SET
                review_status = CASE
                    WHEN status = 'applied' THEN 'approved'
                    ELSE 'pending'
                END,
                reviewed_by_admin_id = CASE
                    WHEN status = 'applied' THEN applied_by_admin_id
                    ELSE reviewed_by_admin_id
                END,
                reviewed_at = CASE
                    WHEN status = 'applied' THEN applied_at
                    ELSE reviewed_at
                END,
                review_note = CASE
                    WHEN status = 'applied'
                    THEN 'Legacy applied import accepted during Sprint 48 migration'
                    ELSE review_note
                END
            """
        )
    )

    # ---------------------------------------------------------------
    # Settlement operations queue / close-lock state
    # ---------------------------------------------------------------
    with op.batch_alter_table("provider_settlement_batches", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "operations_status",
                sa.String(length=20),
                nullable=False,
                server_default="open",
            )
        )
        batch.add_column(sa.Column("assigned_admin_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("closed_by_admin_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("close_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_provider_settlement_assigned_admin",
            "users",
            ["assigned_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_provider_settlement_closed_by",
            "users",
            ["closed_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint(
            "ck_provider_settlement_operations_status",
            "operations_status IN ('open','review','closed','reopened')",
        )
    op.create_index(
        "ix_provider_settlement_batches_operations_status",
        "provider_settlement_batches",
        ["operations_status"],
    )
    op.execute(
        sa.text(
            """
            UPDATE provider_settlement_batches
            SET operations_status = CASE
                WHEN status = 'reconciled' THEN 'review'
                ELSE 'open'
            END
            """
        )
    )

    # ---------------------------------------------------------------
    # Expansion zone traffic policy
    # ---------------------------------------------------------------
    op.create_table(
        "zone_traffic_policies",
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("hourly_order_cap", sa.Integer(), nullable=True),
        sa.Column("chef_daily_order_cap", sa.Integer(), nullable=True),
        sa.Column("enforce_rollout_bucket", sa.Boolean(), nullable=False),
        sa.Column("warning_utilization_pct", sa.Float(), nullable=False),
        sa.Column("critical_utilization_pct", sa.Float(), nullable=False),
        sa.Column("rejection_spike_pct", sa.Float(), nullable=False),
        sa.Column("rejection_spike_min_attempts", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "hourly_order_cap IS NULL OR hourly_order_cap > 0",
            name="ck_zone_traffic_hourly_cap",
        ),
        sa.CheckConstraint(
            "chef_daily_order_cap IS NULL OR chef_daily_order_cap > 0",
            name="ck_zone_traffic_chef_daily_cap",
        ),
        sa.CheckConstraint(
            "warning_utilization_pct > 0 AND warning_utilization_pct <= 100",
            name="ck_zone_traffic_warning_pct",
        ),
        sa.CheckConstraint(
            "critical_utilization_pct > 0 AND critical_utilization_pct <= 100",
            name="ck_zone_traffic_critical_pct",
        ),
        sa.CheckConstraint(
            "rejection_spike_pct > 0 AND rejection_spike_pct <= 100",
            name="ck_zone_traffic_rejection_pct",
        ),
        sa.CheckConstraint(
            "rejection_spike_min_attempts > 0",
            name="ck_zone_traffic_rejection_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["expansion_zones.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("zone_id"),
    )

    # Backfill all existing Expansion Zones with conservative pilot defaults.
    op.execute(
        sa.text(
            """
            INSERT INTO zone_traffic_policies (
                zone_id, is_enabled, hourly_order_cap, chef_daily_order_cap,
                enforce_rollout_bucket, warning_utilization_pct,
                critical_utilization_pct, rejection_spike_pct,
                rejection_spike_min_attempts, note,
                created_by_admin_id, updated_by_admin_id,
                created_at, updated_at
            )
            SELECT
                id, TRUE, 8, 12,
                TRUE, 80.0, 95.0, 30.0,
                5, 'Sprint 48 migration backfill',
                created_by_admin_id, created_by_admin_id,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM expansion_zones
            """
        )
    )

    # ---------------------------------------------------------------
    # Admission decision ledger
    # ---------------------------------------------------------------
    op.create_table(
        "zone_admission_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("rollout_stage", sa.String(length=20), nullable=False),
        sa.Column("rollout_percent", sa.Integer(), nullable=False),
        sa.Column("rollout_bucket", sa.Integer(), nullable=True),
        sa.Column("daily_cap", sa.Integer(), nullable=True),
        sa.Column("daily_usage_before", sa.Integer(), nullable=False),
        sa.Column("hourly_cap", sa.Integer(), nullable=True),
        sa.Column("hourly_usage_before", sa.Integer(), nullable=False),
        sa.Column("chef_daily_cap", sa.Integer(), nullable=True),
        sa.Column("chef_usage_before", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('admitted','rejected')",
            name="ck_zone_admission_decision",
        ),
        sa.CheckConstraint(
            "rollout_percent BETWEEN 0 AND 100",
            name="ck_zone_admission_rollout_percent",
        ),
        sa.CheckConstraint(
            "rollout_bucket IS NULL OR rollout_bucket BETWEEN 0 AND 99",
            name="ck_zone_admission_rollout_bucket",
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["expansion_zones.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_zone_admission_events_zone_id", "zone_admission_events", ["zone_id"])
    op.create_index("ix_zone_admission_events_order_id", "zone_admission_events", ["order_id"])
    op.create_index("ix_zone_admission_events_customer_id", "zone_admission_events", ["customer_id"])
    op.create_index("ix_zone_admission_events_chef_id", "zone_admission_events", ["chef_id"])
    op.create_index("ix_zone_admission_events_service_date", "zone_admission_events", ["service_date"])
    op.create_index("ix_zone_admission_events_decision", "zone_admission_events", ["decision"])
    op.create_index("ix_zone_admission_events_reason", "zone_admission_events", ["reason"])
    op.create_index("ix_zone_admission_events_created_at", "zone_admission_events", ["created_at"])
    op.create_index(
        "ix_zone_admission_zone_created",
        "zone_admission_events",
        ["zone_id", "created_at"],
    )
    op.create_index(
        "ix_zone_admission_zone_service_decision",
        "zone_admission_events",
        ["zone_id", "service_date", "decision"],
    )

    # ---------------------------------------------------------------
    # Expansion monitoring snapshots
    # ---------------------------------------------------------------
    op.create_table(
        "expansion_monitoring_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("rollout_stage", sa.String(length=20), nullable=False),
        sa.Column("rollout_percent", sa.Integer(), nullable=False),
        sa.Column("zone_daily_cap", sa.Integer(), nullable=True),
        sa.Column("admitted_orders_today", sa.Integer(), nullable=False),
        sa.Column("daily_utilization_pct", sa.Float(), nullable=False),
        sa.Column("hourly_cap", sa.Integer(), nullable=True),
        sa.Column("admitted_orders_last_hour", sa.Integer(), nullable=False),
        sa.Column("hourly_utilization_pct", sa.Float(), nullable=False),
        sa.Column("admission_attempts_last_hour", sa.Integer(), nullable=False),
        sa.Column("admission_rejections_last_hour", sa.Integer(), nullable=False),
        sa.Column("rejection_rate_pct", sa.Float(), nullable=False),
        sa.Column("available_drivers", sa.Integer(), nullable=False),
        sa.Column("open_chefs", sa.Integer(), nullable=False),
        sa.Column("top_chef_orders", sa.Integer(), nullable=False),
        sa.Column("chef_daily_cap", sa.Integer(), nullable=True),
        sa.Column("top_chef_utilization_pct", sa.Float(), nullable=False),
        sa.Column("health", sa.String(length=20), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("generated_by", sa.String(length=20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "health IN ('green','amber','red')",
            name="ck_expansion_monitoring_health",
        ),
        sa.CheckConstraint(
            "daily_utilization_pct >= 0",
            name="ck_expansion_monitoring_daily_util",
        ),
        sa.CheckConstraint(
            "hourly_utilization_pct >= 0",
            name="ck_expansion_monitoring_hourly_util",
        ),
        sa.CheckConstraint(
            "rejection_rate_pct BETWEEN 0 AND 100",
            name="ck_expansion_monitoring_reject_rate",
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["expansion_zones.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_expansion_monitoring_snapshots_zone_id",
        "expansion_monitoring_snapshots",
        ["zone_id"],
    )
    op.create_index(
        "ix_expansion_monitoring_snapshots_service_date",
        "expansion_monitoring_snapshots",
        ["service_date"],
    )
    op.create_index(
        "ix_expansion_monitoring_snapshots_health",
        "expansion_monitoring_snapshots",
        ["health"],
    )
    op.create_index(
        "ix_expansion_monitoring_snapshots_observed_at",
        "expansion_monitoring_snapshots",
        ["observed_at"],
    )
    op.create_index(
        "ix_expansion_monitoring_zone_observed",
        "expansion_monitoring_snapshots",
        ["zone_id", "observed_at"],
    )

    # Sprint 48 traffic/capacity health becomes a first-class Control Room category.
    with op.batch_alter_table("operations_incidents", recreate="auto") as batch:
        batch.drop_constraint("ck_operations_incidents_category", type_="check")
        batch.create_check_constraint(
            "ck_operations_incidents_category",
            "category IN ("
            "'chef_sla','delivery_sla','support_sla','payment',"
            "'reliability','notifications','traffic'"
            ")",
        )


def downgrade() -> None:
    with op.batch_alter_table("operations_incidents", recreate="auto") as batch:
        batch.drop_constraint("ck_operations_incidents_category", type_="check")
        batch.create_check_constraint(
            "ck_operations_incidents_category",
            "category IN ("
            "'chef_sla','delivery_sla','support_sla','payment',"
            "'reliability','notifications'"
            ")",
        )

    op.drop_index(
        "ix_expansion_monitoring_zone_observed",
        table_name="expansion_monitoring_snapshots",
    )
    op.drop_index(
        "ix_expansion_monitoring_snapshots_observed_at",
        table_name="expansion_monitoring_snapshots",
    )
    op.drop_index(
        "ix_expansion_monitoring_snapshots_health",
        table_name="expansion_monitoring_snapshots",
    )
    op.drop_index(
        "ix_expansion_monitoring_snapshots_service_date",
        table_name="expansion_monitoring_snapshots",
    )
    op.drop_index(
        "ix_expansion_monitoring_snapshots_zone_id",
        table_name="expansion_monitoring_snapshots",
    )
    op.drop_table("expansion_monitoring_snapshots")

    op.drop_index(
        "ix_zone_admission_zone_service_decision",
        table_name="zone_admission_events",
    )
    op.drop_index(
        "ix_zone_admission_zone_created",
        table_name="zone_admission_events",
    )
    op.drop_index("ix_zone_admission_events_created_at", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_reason", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_decision", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_service_date", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_chef_id", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_customer_id", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_order_id", table_name="zone_admission_events")
    op.drop_index("ix_zone_admission_events_zone_id", table_name="zone_admission_events")
    op.drop_table("zone_admission_events")

    op.drop_table("zone_traffic_policies")

    op.drop_index(
        "ix_provider_settlement_batches_operations_status",
        table_name="provider_settlement_batches",
    )
    with op.batch_alter_table("provider_settlement_batches", recreate="auto") as batch:
        batch.drop_constraint("ck_provider_settlement_operations_status", type_="check")
        batch.drop_constraint("fk_provider_settlement_closed_by", type_="foreignkey")
        batch.drop_constraint("fk_provider_settlement_assigned_admin", type_="foreignkey")
        batch.drop_column("closed_at")
        batch.drop_column("close_note")
        batch.drop_column("closed_by_admin_id")
        batch.drop_column("assigned_admin_id")
        batch.drop_column("operations_status")

    op.drop_index(
        "ix_provider_cost_import_batches_review_status",
        table_name="provider_cost_import_batches",
    )
    with op.batch_alter_table("provider_cost_import_batches", recreate="auto") as batch:
        batch.drop_constraint("ck_provider_cost_import_review_status", type_="check")
        batch.drop_constraint("fk_provider_cost_import_reviewed_by", type_="foreignkey")
        batch.drop_constraint("fk_provider_cost_import_assigned_reviewer", type_="foreignkey")
        batch.drop_column("reviewed_at")
        batch.drop_column("risk_flags_json")
        batch.drop_column("review_note")
        batch.drop_column("reviewed_by_admin_id")
        batch.drop_column("assigned_reviewer_id")
        batch.drop_column("review_status")


