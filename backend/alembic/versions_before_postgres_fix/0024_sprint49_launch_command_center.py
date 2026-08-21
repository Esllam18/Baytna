"""Sprint 49 pilot launch command center and evidence orchestration.

Revision ID: 0024_sprint49
Revises: 0023_sprint48
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_sprint49"
down_revision = "0023_sprint48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "launch_command_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pilot_program_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("launch_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("incident_commander_admin_id", sa.Uuid(), nullable=False),
        sa.Column("finance_admin_id", sa.Uuid(), nullable=True),
        sa.Column("operations_admin_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aborted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned','active','paused','completed','aborted')",
            name="ck_launch_command_session_status",
        ),
        sa.ForeignKeyConstraint(
            ["pilot_program_id"], ["pilot_programs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["expansion_zones.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["incident_commander_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["finance_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["operations_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_launch_command_sessions_pilot_program_id", "launch_command_sessions", ["pilot_program_id"])
    op.create_index("ix_launch_command_sessions_zone_id", "launch_command_sessions", ["zone_id"])
    op.create_index("ix_launch_command_sessions_launch_date", "launch_command_sessions", ["launch_date"])
    op.create_index("ix_launch_command_sessions_status", "launch_command_sessions", ["status"])
    op.create_index(
        "ix_launch_command_zone_status",
        "launch_command_sessions",
        ["zone_id", "status"],
    )

    op.create_table(
        "launch_runbook_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("step_key", sa.String(length=80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_reference", sa.String(length=500), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("completed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence > 0", name="ck_launch_runbook_sequence"),
        sa.CheckConstraint(
            "status IN ('pending','passed','failed','skipped')",
            name="ck_launch_runbook_status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["launch_command_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "step_key", name="uq_launch_runbook_step_key"
        ),
    )
    op.create_index("ix_launch_runbook_steps_session_id", "launch_runbook_steps", ["session_id"])
    op.create_index("ix_launch_runbook_steps_status", "launch_runbook_steps", ["status"])

    op.create_table(
        "launch_command_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info','warning','high','critical')",
            name="ck_launch_command_event_severity",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["launch_command_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_launch_command_events_session_id", "launch_command_events", ["session_id"])
    op.create_index("ix_launch_command_events_event_type", "launch_command_events", ["event_type"])
    op.create_index("ix_launch_command_events_created_at", "launch_command_events", ["created_at"])

    op.create_table(
        "launch_traffic_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("override_type", sa.String(length=40), nullable=False),
        sa.Column("previous_value_json", sa.JSON(), nullable=False),
        sa.Column("override_value_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("reverted_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "override_type IN ('daily_order_cap','hourly_order_cap','chef_daily_order_cap','admission_enabled')",
            name="ck_launch_traffic_override_type",
        ),
        sa.CheckConstraint(
            "status IN ('active','reverted','expired')",
            name="ck_launch_traffic_override_status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["launch_command_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["activated_by_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reverted_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_launch_traffic_overrides_session_id", "launch_traffic_overrides", ["session_id"])
    op.create_index("ix_launch_traffic_overrides_zone_id", "launch_traffic_overrides", ["zone_id"])
    op.create_index("ix_launch_traffic_overrides_override_type", "launch_traffic_overrides", ["override_type"])
    op.create_index("ix_launch_traffic_overrides_status", "launch_traffic_overrides", ["status"])
    op.create_index("ix_launch_traffic_overrides_expires_at", "launch_traffic_overrides", ["expires_at"])
    op.create_index(
        "ix_launch_override_zone_status",
        "launch_traffic_overrides",
        ["zone_id", "status"],
    )

    op.create_table(
        "daily_financial_closes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("pilot_program_id", sa.Uuid(), nullable=False),
        sa.Column("close_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("delivered_orders", sa.Integer(), nullable=False),
        sa.Column("succeeded_payment_orders", sa.Integer(), nullable=False),
        sa.Column("captured_minor", sa.Integer(), nullable=False),
        sa.Column("refunded_minor", sa.Integer(), nullable=False),
        sa.Column("net_collected_minor", sa.Integer(), nullable=False),
        sa.Column("verified_cost_minor", sa.Integer(), nullable=False),
        sa.Column("contribution_minor", sa.Integer(), nullable=False),
        sa.Column("operational_profit_minor", sa.Integer(), nullable=False),
        sa.Column("revenue_coverage_pct", sa.Float(), nullable=False),
        sa.Column("cost_coverage_pct", sa.Float(), nullable=False),
        sa.Column("unverified_cost_entries", sa.Integer(), nullable=False),
        sa.Column("pending_provider_imports", sa.Integer(), nullable=False),
        sa.Column("unclosed_settlements", sa.Integer(), nullable=False),
        sa.Column("open_payment_issues", sa.Integer(), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("prepared_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("closed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reopened_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','ready','blocked','closed','reopened')",
            name="ck_daily_financial_close_status",
        ),
        sa.CheckConstraint(
            "revenue_coverage_pct BETWEEN 0 AND 100",
            name="ck_daily_close_revenue_coverage",
        ),
        sa.CheckConstraint(
            "cost_coverage_pct BETWEEN 0 AND 100",
            name="ck_daily_close_cost_coverage",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["launch_command_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pilot_program_id"], ["pilot_programs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["prepared_by_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reopened_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "close_date", name="uq_daily_financial_close_session_date"
        ),
    )
    op.create_index("ix_daily_financial_closes_session_id", "daily_financial_closes", ["session_id"])
    op.create_index("ix_daily_financial_closes_pilot_program_id", "daily_financial_closes", ["pilot_program_id"])
    op.create_index("ix_daily_financial_closes_close_date", "daily_financial_closes", ["close_date"])
    op.create_index("ix_daily_financial_closes_status", "daily_financial_closes", ["status"])

    op.create_table(
        "launch_rollback_drills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("target_recovery_seconds", sa.Integer(), nullable=False),
        sa.Column("recovery_seconds", sa.Integer(), nullable=True),
        sa.Column("pre_state_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=500), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("initiated_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("verified_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "mode IN ('tabletop','live_controlled')",
            name="ck_launch_rollback_drill_mode",
        ),
        sa.CheckConstraint(
            "status IN ('running','passed','failed','aborted')",
            name="ck_launch_rollback_drill_status",
        ),
        sa.CheckConstraint(
            "target_recovery_seconds > 0",
            name="ck_launch_rollback_target",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["launch_command_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["expansion_zones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["verified_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_launch_rollback_drills_session_id", "launch_rollback_drills", ["session_id"])
    op.create_index("ix_launch_rollback_drills_zone_id", "launch_rollback_drills", ["zone_id"])
    op.create_index("ix_launch_rollback_drills_status", "launch_rollback_drills", ["status"])

    op.create_table(
        "launch_evidence_packs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("release_version", sa.String(length=30), nullable=False),
        sa.Column("migration_head", sa.String(length=40), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("generated_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('complete','incomplete')",
            name="ck_launch_evidence_pack_status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["launch_command_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["generated_by_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_launch_evidence_packs_session_id", "launch_evidence_packs", ["session_id"])
    op.create_index("ix_launch_evidence_packs_status", "launch_evidence_packs", ["status"])
    op.create_index(
        "ix_launch_evidence_session_generated",
        "launch_evidence_packs",
        ["session_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_launch_evidence_session_generated", table_name="launch_evidence_packs")
    op.drop_index("ix_launch_evidence_packs_status", table_name="launch_evidence_packs")
    op.drop_index("ix_launch_evidence_packs_session_id", table_name="launch_evidence_packs")
    op.drop_table("launch_evidence_packs")

    op.drop_index("ix_launch_rollback_drills_status", table_name="launch_rollback_drills")
    op.drop_index("ix_launch_rollback_drills_zone_id", table_name="launch_rollback_drills")
    op.drop_index("ix_launch_rollback_drills_session_id", table_name="launch_rollback_drills")
    op.drop_table("launch_rollback_drills")

    op.drop_index("ix_daily_financial_closes_status", table_name="daily_financial_closes")
    op.drop_index("ix_daily_financial_closes_close_date", table_name="daily_financial_closes")
    op.drop_index("ix_daily_financial_closes_pilot_program_id", table_name="daily_financial_closes")
    op.drop_index("ix_daily_financial_closes_session_id", table_name="daily_financial_closes")
    op.drop_table("daily_financial_closes")

    op.drop_index("ix_launch_override_zone_status", table_name="launch_traffic_overrides")
    op.drop_index("ix_launch_traffic_overrides_expires_at", table_name="launch_traffic_overrides")
    op.drop_index("ix_launch_traffic_overrides_status", table_name="launch_traffic_overrides")
    op.drop_index("ix_launch_traffic_overrides_override_type", table_name="launch_traffic_overrides")
    op.drop_index("ix_launch_traffic_overrides_zone_id", table_name="launch_traffic_overrides")
    op.drop_index("ix_launch_traffic_overrides_session_id", table_name="launch_traffic_overrides")
    op.drop_table("launch_traffic_overrides")

    op.drop_index("ix_launch_command_events_created_at", table_name="launch_command_events")
    op.drop_index("ix_launch_command_events_event_type", table_name="launch_command_events")
    op.drop_index("ix_launch_command_events_session_id", table_name="launch_command_events")
    op.drop_table("launch_command_events")

    op.drop_index("ix_launch_runbook_steps_status", table_name="launch_runbook_steps")
    op.drop_index("ix_launch_runbook_steps_session_id", table_name="launch_runbook_steps")
    op.drop_table("launch_runbook_steps")

    op.drop_index("ix_launch_command_zone_status", table_name="launch_command_sessions")
    op.drop_index("ix_launch_command_sessions_status", table_name="launch_command_sessions")
    op.drop_index("ix_launch_command_sessions_launch_date", table_name="launch_command_sessions")
    op.drop_index("ix_launch_command_sessions_zone_id", table_name="launch_command_sessions")
    op.drop_index("ix_launch_command_sessions_pilot_program_id", table_name="launch_command_sessions")
    op.drop_table("launch_command_sessions")
