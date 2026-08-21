"""Sprint 47 provider imports, settlements, budgets and rollout controls.

Revision ID: 0022_sprint47
Revises: 0021_sprint46
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_sprint47"
down_revision = "0021_sprint46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend operational economics cost taxonomy.
    with op.batch_alter_table("economics_cost_entries", recreate="auto") as batch:
        batch.drop_constraint("ck_economics_cost_type", type_="check")
        batch.create_check_constraint(
            "ck_economics_cost_type",
            "cost_type IN ("
            "'chef_payout','delivery_partner','payment_processing','packaging',"
            "'refund_fee','customer_recovery','other_variable','fixed_operations',"
            "'communications_provider','cloud_storage','cloud_infrastructure',"
            "'provider_adjustment'"
            ")",
        )

    op.create_table(
        "provider_cost_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("pilot_program_id", sa.Uuid(), nullable=True),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate_to_egp", sa.Float(), nullable=True),
        sa.Column("fx_reference", sa.String(length=240), nullable=True),
        sa.Column("external_reference", sa.String(length=180), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column("total_source_minor", sa.Integer(), nullable=False),
        sa.Column("total_egp_minor", sa.Integer(), nullable=False),
        sa.Column("applied_cost_entries", sa.Integer(), nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("validated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("applied_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','validated','applied','failed')",
            name="ck_provider_cost_import_status",
        ),
        sa.CheckConstraint("rows_count >= 0", name="ck_provider_cost_import_rows"),
        sa.CheckConstraint(
            "total_source_minor >= 0",
            name="ck_provider_cost_import_source_total",
        ),
        sa.CheckConstraint(
            "total_egp_minor >= 0",
            name="ck_provider_cost_import_egp_total",
        ),
        sa.ForeignKeyConstraint(
            ["pilot_program_id"], ["pilot_programs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["validated_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["applied_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "external_reference",
            name="uq_provider_cost_import_reference",
        ),
    )
    op.create_index(
        "ix_provider_cost_import_batches_provider",
        "provider_cost_import_batches",
        ["provider"],
    )
    op.create_index(
        "ix_provider_cost_import_batches_pilot_program_id",
        "provider_cost_import_batches",
        ["pilot_program_id"],
    )
    op.create_index(
        "ix_provider_cost_import_batches_status",
        "provider_cost_import_batches",
        ["status"],
    )

    op.create_table(
        "provider_cost_import_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("line_key", sa.String(length=180), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("incurred_on", sa.Date(), nullable=False),
        sa.Column("cost_type", sa.String(length=40), nullable=False),
        sa.Column("source_amount_minor", sa.Integer(), nullable=False),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("egp_amount_minor", sa.Integer(), nullable=False),
        sa.Column("external_reference", sa.String(length=220), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("applied_cost_entry_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_amount_minor > 0",
            name="ck_provider_cost_import_line_source_amount",
        ),
        sa.CheckConstraint(
            "egp_amount_minor > 0",
            name="ck_provider_cost_import_line_egp_amount",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["provider_cost_import_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["applied_cost_entry_id"],
            ["economics_cost_entries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id", "line_key", name="uq_provider_cost_import_line_key"
        ),
    )
    op.create_index(
        "ix_provider_cost_import_lines_batch_id",
        "provider_cost_import_lines",
        ["batch_id"],
    )
    op.create_index(
        "ix_provider_cost_import_lines_order_id",
        "provider_cost_import_lines",
        ["order_id"],
    )

    op.create_table(
        "provider_settlement_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("pilot_program_id", sa.Uuid(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("external_reference", sa.String(length=180), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column("matched_lines", sa.Integer(), nullable=False),
        sa.Column("mismatched_lines", sa.Integer(), nullable=False),
        sa.Column("gross_minor", sa.Integer(), nullable=False),
        sa.Column("fees_minor", sa.Integer(), nullable=False),
        sa.Column("refunds_minor", sa.Integer(), nullable=False),
        sa.Column("net_settlement_minor", sa.Integer(), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reconciled_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','reconciled','blocked')",
            name="ck_provider_settlement_status",
        ),
        sa.CheckConstraint("rows_count >= 0", name="ck_provider_settlement_rows"),
        sa.CheckConstraint("fees_minor >= 0", name="ck_provider_settlement_fees"),
        sa.CheckConstraint(
            "refunds_minor >= 0", name="ck_provider_settlement_refunds"
        ),
        sa.ForeignKeyConstraint(
            ["pilot_program_id"], ["pilot_programs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reconciled_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "external_reference",
            name="uq_provider_settlement_reference",
        ),
    )
    op.create_index(
        "ix_provider_settlement_batches_provider",
        "provider_settlement_batches",
        ["provider"],
    )
    op.create_index(
        "ix_provider_settlement_batches_pilot_program_id",
        "provider_settlement_batches",
        ["pilot_program_id"],
    )
    op.create_index(
        "ix_provider_settlement_batches_status",
        "provider_settlement_batches",
        ["status"],
    )

    op.create_table(
        "provider_settlement_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("provider_transaction_id", sa.String(length=180), nullable=False),
        sa.Column("settlement_reference", sa.String(length=180), nullable=True),
        sa.Column("gross_amount_minor", sa.Integer(), nullable=False),
        sa.Column("fee_minor", sa.Integer(), nullable=False),
        sa.Column("refund_minor", sa.Integer(), nullable=False),
        sa.Column("net_settlement_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_settled", sa.Boolean(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched_payment_id", sa.Uuid(), nullable=True),
        sa.Column("reconciliation_status", sa.String(length=20), nullable=False),
        sa.Column("issues_json", sa.JSON(), nullable=False),
        sa.Column("applied_cost_entry_id", sa.Uuid(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "gross_amount_minor >= 0", name="ck_provider_settlement_gross"
        ),
        sa.CheckConstraint(
            "fee_minor >= 0", name="ck_provider_settlement_fee"
        ),
        sa.CheckConstraint(
            "refund_minor >= 0", name="ck_provider_settlement_refund"
        ),
        sa.CheckConstraint(
            "reconciliation_status IN ('pending','matched','mismatch','unmatched')",
            name="ck_provider_settlement_line_status",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["provider_settlement_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["matched_payment_id"], ["payments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["applied_cost_entry_id"],
            ["economics_cost_entries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "provider_transaction_id",
            name="uq_provider_settlement_line_tx",
        ),
    )
    op.create_index(
        "ix_provider_settlement_lines_batch_id",
        "provider_settlement_lines",
        ["batch_id"],
    )
    op.create_index(
        "ix_provider_settlement_lines_reconciliation_status",
        "provider_settlement_lines",
        ["reconciliation_status"],
    )

    # Expansion rollout columns.
    with op.batch_alter_table("expansion_zones", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "rollout_stage",
                sa.String(length=20),
                nullable=False,
                server_default="not_started",
            )
        )
        batch.add_column(
            sa.Column(
                "rollout_percent",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(sa.Column("daily_order_cap", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "rollout_started_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "rollout_completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.create_check_constraint(
            "ck_expansion_zone_rollout_stage",
            "rollout_stage IN ('not_started','canary','limited','full','paused')",
        )
        batch.create_check_constraint(
            "ck_expansion_zone_rollout_percent",
            "rollout_percent BETWEEN 0 AND 100",
        )
    op.create_index(
        "ix_expansion_zones_rollout_stage",
        "expansion_zones",
        ["rollout_stage"],
    )

    op.create_table(
        "expansion_zone_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("allocated_minor", sa.Integer(), nullable=False),
        sa.Column("committed_minor", sa.Integer(), nullable=False),
        sa.Column("spent_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "allocated_minor > 0", name="ck_expansion_budget_allocated"
        ),
        sa.CheckConstraint(
            "committed_minor >= 0", name="ck_expansion_budget_committed"
        ),
        sa.CheckConstraint(
            "spent_minor >= 0", name="ck_expansion_budget_spent"
        ),
        sa.CheckConstraint(
            "currency = 'EGP'", name="ck_expansion_budget_currency"
        ),
        sa.CheckConstraint(
            "committed_minor + spent_minor <= allocated_minor",
            name="ck_expansion_budget_not_overspent",
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "zone_id", "category", name="uq_expansion_zone_budget_category"
        ),
    )
    op.create_index(
        "ix_expansion_zone_budgets_zone_id",
        "expansion_zone_budgets",
        ["zone_id"],
    )

    op.create_table(
        "expansion_rollout_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("from_stage", sa.String(length=20), nullable=False),
        sa.Column("to_stage", sa.String(length=20), nullable=False),
        sa.Column("rollout_percent", sa.Integer(), nullable=False),
        sa.Column("daily_order_cap", sa.Integer(), nullable=True),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("budget_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("triggered_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rollout_percent BETWEEN 0 AND 100",
            name="ck_expansion_rollout_percent",
        ),
        sa.CheckConstraint(
            "from_stage IN ('not_started','canary','limited','full','paused')",
            name="ck_expansion_rollout_from_stage",
        ),
        sa.CheckConstraint(
            "to_stage IN ('not_started','canary','limited','full','paused')",
            name="ck_expansion_rollout_to_stage",
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["expansion_assessments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_expansion_rollout_events_zone_id",
        "expansion_rollout_events",
        ["zone_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_expansion_rollout_events_zone_id",
        table_name="expansion_rollout_events",
    )
    op.drop_table("expansion_rollout_events")

    op.drop_index(
        "ix_expansion_zone_budgets_zone_id",
        table_name="expansion_zone_budgets",
    )
    op.drop_table("expansion_zone_budgets")

    op.drop_index(
        "ix_expansion_zones_rollout_stage",
        table_name="expansion_zones",
    )
    with op.batch_alter_table("expansion_zones", recreate="auto") as batch:
        batch.drop_constraint(
            "ck_expansion_zone_rollout_percent", type_="check"
        )
        batch.drop_constraint(
            "ck_expansion_zone_rollout_stage", type_="check"
        )
        batch.drop_column("rollout_completed_at")
        batch.drop_column("rollout_started_at")
        batch.drop_column("daily_order_cap")
        batch.drop_column("rollout_percent")
        batch.drop_column("rollout_stage")

    op.drop_index(
        "ix_provider_settlement_lines_reconciliation_status",
        table_name="provider_settlement_lines",
    )
    op.drop_index(
        "ix_provider_settlement_lines_batch_id",
        table_name="provider_settlement_lines",
    )
    op.drop_table("provider_settlement_lines")

    op.drop_index(
        "ix_provider_settlement_batches_status",
        table_name="provider_settlement_batches",
    )
    op.drop_index(
        "ix_provider_settlement_batches_pilot_program_id",
        table_name="provider_settlement_batches",
    )
    op.drop_index(
        "ix_provider_settlement_batches_provider",
        table_name="provider_settlement_batches",
    )
    op.drop_table("provider_settlement_batches")

    op.drop_index(
        "ix_provider_cost_import_lines_order_id",
        table_name="provider_cost_import_lines",
    )
    op.drop_index(
        "ix_provider_cost_import_lines_batch_id",
        table_name="provider_cost_import_lines",
    )
    op.drop_table("provider_cost_import_lines")

    op.drop_index(
        "ix_provider_cost_import_batches_status",
        table_name="provider_cost_import_batches",
    )
    op.drop_index(
        "ix_provider_cost_import_batches_pilot_program_id",
        table_name="provider_cost_import_batches",
    )
    op.drop_index(
        "ix_provider_cost_import_batches_provider",
        table_name="provider_cost_import_batches",
    )
    op.drop_table("provider_cost_import_batches")

    with op.batch_alter_table("economics_cost_entries", recreate="auto") as batch:
        batch.drop_constraint("ck_economics_cost_type", type_="check")
        batch.create_check_constraint(
            "ck_economics_cost_type",
            "cost_type IN ("
            "'chef_payout','delivery_partner','payment_processing','packaging',"
            "'refund_fee','customer_recovery','other_variable','fixed_operations'"
            ")",
        )

