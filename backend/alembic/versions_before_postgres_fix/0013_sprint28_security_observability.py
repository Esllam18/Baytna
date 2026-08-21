"""Sprint 28 security hardening, persistent rate limits and security events.

Revision ID: 0013_sprint28
Revises: 0012_sprint27
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_sprint28"
down_revision = "0012_sprint27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "window_seconds > 0",
            name="ck_rate_limit_window_positive",
        ),
        sa.CheckConstraint(
            "request_count >= 0",
            name="ck_rate_limit_count_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope",
            "key_hash",
            "window_start",
            name="uq_rate_limit_scope_key_window",
        ),
    )
    op.create_index(
        "ix_rate_limit_expiry",
        "rate_limit_buckets",
        ["expires_at"],
    )
    op.create_index(
        "ix_rate_limit_scope_window",
        "rate_limit_buckets",
        ["scope", "window_start"],
    )

    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("path", sa.String(length=300), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_security_event_severity",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_security_events_event_type",
        "security_events",
        ["event_type"],
    )
    op.create_index(
        "ix_security_events_request_id",
        "security_events",
        ["request_id"],
    )
    op.create_index(
        "ix_security_events_actor_user_id",
        "security_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_security_events_created",
        "security_events",
        ["created_at"],
    )
    op.create_index(
        "ix_security_events_type_created",
        "security_events",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_events_type_created",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_created",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_actor_user_id",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_request_id",
        table_name="security_events",
    )
    op.drop_index(
        "ix_security_events_event_type",
        table_name="security_events",
    )
    op.drop_table("security_events")

    op.drop_index(
        "ix_rate_limit_scope_window",
        table_name="rate_limit_buckets",
    )
    op.drop_index(
        "ix_rate_limit_expiry",
        table_name="rate_limit_buckets",
    )
    op.drop_table("rate_limit_buckets")
