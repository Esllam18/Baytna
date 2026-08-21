"""Sprint 46 operational economics and expansion readiness.

Revision ID: 0021_sprint46
Revises: 0020_sprint45
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_sprint46"
down_revision = "0020_sprint45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economics_cost_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pilot_program_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column("incurred_on", sa.Date(), nullable=False),
        sa.Column("cost_type", sa.String(length=40), nullable=False),
        sa.Column("cost_scope", sa.String(length=20), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("external_reference", sa.String(length=180), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("verified_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_economics_cost_amount"),
        sa.CheckConstraint("currency = 'EGP'", name="ck_economics_cost_currency"),
        sa.CheckConstraint("cost_scope IN ('variable','fixed')", name="ck_economics_cost_scope"),
        sa.CheckConstraint(
            "cost_type IN ('chef_payout','delivery_partner','payment_processing','packaging','refund_fee','customer_recovery','other_variable','fixed_operations')",
            name="ck_economics_cost_type",
        ),
        sa.CheckConstraint(
            "source IN ('manual','provider','import')",
            name="ck_economics_cost_source",
        ),
        sa.ForeignKeyConstraint(["pilot_program_id"], ["pilot_programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_economics_cost_entries_pilot_program_id", "economics_cost_entries", ["pilot_program_id"])
    op.create_index("ix_economics_cost_entries_order_id", "economics_cost_entries", ["order_id"])
    op.create_index("ix_economics_cost_entries_area", "economics_cost_entries", ["area"])
    op.create_index("ix_economics_cost_entries_incurred_on", "economics_cost_entries", ["incurred_on"])
    op.create_index("ix_economics_cost_entries_cost_type", "economics_cost_entries", ["cost_type"])
    op.create_index("ix_economics_cost_entries_cost_scope", "economics_cost_entries", ["cost_scope"])
    op.create_index("ix_economics_cost_program_date", "economics_cost_entries", ["pilot_program_id", "incurred_on"])
    op.create_index("ix_economics_cost_order_type", "economics_cost_entries", ["order_id", "cost_type"])

    op.create_table(
        "expansion_zones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=False),
        sa.Column("source_program_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("min_delivered_orders", sa.Integer(), nullable=False),
        sa.Column("min_contribution_margin_pct", sa.Float(), nullable=False),
        sa.Column("min_operational_profit_minor", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('candidate','ready','approved','live','paused','rejected')",
            name="ck_expansion_zone_status",
        ),
        sa.CheckConstraint("min_delivered_orders > 0", name="ck_expansion_zone_min_orders"),
        sa.CheckConstraint(
            "min_contribution_margin_pct BETWEEN -100 AND 100",
            name="ck_expansion_zone_margin",
        ),
        sa.ForeignKeyConstraint(["source_program_id"], ["pilot_programs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("area"),
    )
    op.create_index("ix_expansion_zones_area", "expansion_zones", ["area"], unique=True)
    op.create_index("ix_expansion_zones_source_program_id", "expansion_zones", ["source_program_id"])
    op.create_index("ix_expansion_zones_status", "expansion_zones", ["status"])

    op.create_table(
        "expansion_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("delivered_orders", sa.Integer(), nullable=False),
        sa.Column("net_collected_minor", sa.Integer(), nullable=False),
        sa.Column("variable_cost_minor", sa.Integer(), nullable=False),
        sa.Column("contribution_minor", sa.Integer(), nullable=False),
        sa.Column("contribution_margin_pct", sa.Float(), nullable=True),
        sa.Column("fixed_cost_minor", sa.Integer(), nullable=False),
        sa.Column("operational_profit_minor", sa.Integer(), nullable=False),
        sa.Column("cost_coverage_pct", sa.Float(), nullable=False),
        sa.Column("revenue_coverage_pct", sa.Float(), nullable=False),
        sa.Column("unverified_cost_entries", sa.Integer(), nullable=False),
        sa.Column("economics_evaluable", sa.Boolean(), nullable=False),
        sa.Column("stability_gate_met", sa.Boolean(), nullable=False),
        sa.Column("post_pilot_scale_ready", sa.Boolean(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by_admin_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("decision IN ('ready','blocked')", name="ck_expansion_assessment_decision"),
        sa.CheckConstraint("cost_coverage_pct BETWEEN 0 AND 100", name="ck_expansion_assessment_cost_coverage"),
        sa.CheckConstraint("revenue_coverage_pct BETWEEN 0 AND 100", name="ck_expansion_assessment_revenue_coverage"),
        sa.ForeignKeyConstraint(["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["pilot_programs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generated_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expansion_assessments_zone_id", "expansion_assessments", ["zone_id"])
    op.create_index("ix_expansion_assessments_program_id", "expansion_assessments", ["program_id"])
    op.create_index("ix_expansion_assessment_zone_generated", "expansion_assessments", ["zone_id", "generated_at"])


def downgrade() -> None:
    op.drop_index("ix_expansion_assessment_zone_generated", table_name="expansion_assessments")
    op.drop_index("ix_expansion_assessments_program_id", table_name="expansion_assessments")
    op.drop_index("ix_expansion_assessments_zone_id", table_name="expansion_assessments")
    op.drop_table("expansion_assessments")

    op.drop_index("ix_expansion_zones_status", table_name="expansion_zones")
    op.drop_index("ix_expansion_zones_source_program_id", table_name="expansion_zones")
    op.drop_index("ix_expansion_zones_area", table_name="expansion_zones")
    op.drop_table("expansion_zones")

    op.drop_index("ix_economics_cost_order_type", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_program_date", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_entries_cost_scope", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_entries_cost_type", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_entries_incurred_on", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_entries_area", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_entries_order_id", table_name="economics_cost_entries")
    op.drop_index("ix_economics_cost_entries_pilot_program_id", table_name="economics_cost_entries")
    op.drop_table("economics_cost_entries")
