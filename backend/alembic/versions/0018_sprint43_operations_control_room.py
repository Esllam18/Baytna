"""Sprint 43 operations control room incidents.

Revision ID: 0018_sprint43
Revises: 0017_sprint32
"""
from alembic import op
import sqlalchemy as sa


revision = "0018_sprint43"
down_revision = "0017_sprint32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations_incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=220), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=60), nullable=False),
        sa.Column("source_id", sa.String(length=160), nullable=True),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("owner_admin_id", sa.Uuid(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('chef_sla','delivery_sla','support_sla','payment','reliability','notifications')",
            name="ck_operations_incidents_category",
        ),
        sa.CheckConstraint(
            "severity IN ('info','warning','high','critical')",
            name="ck_operations_incidents_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open','acknowledged','resolved')",
            name="ck_operations_incidents_status",
        ),
        sa.ForeignKeyConstraint(
            ["owner_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index(
        "ix_operations_incidents_category",
        "operations_incidents",
        ["category"],
    )
    op.create_index(
        "ix_operations_incidents_severity",
        "operations_incidents",
        ["severity"],
    )
    op.create_index(
        "ix_operations_incidents_status",
        "operations_incidents",
        ["status"],
    )
    op.create_index(
        "ix_operations_incidents_owner_admin_id",
        "operations_incidents",
        ["owner_admin_id"],
    )
    op.create_index(
        "ix_operations_incidents_active",
        "operations_incidents",
        ["status", "severity", "last_detected_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operations_incidents_active",
        table_name="operations_incidents",
    )
    op.drop_index(
        "ix_operations_incidents_owner_admin_id",
        table_name="operations_incidents",
    )
    op.drop_index(
        "ix_operations_incidents_status",
        table_name="operations_incidents",
    )
    op.drop_index(
        "ix_operations_incidents_severity",
        table_name="operations_incidents",
    )
    op.drop_index(
        "ix_operations_incidents_category",
        table_name="operations_incidents",
    )
    op.drop_table("operations_incidents")
