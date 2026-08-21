"""Sprint 31 real provider runtime status fields.

Revision ID: 0016_sprint31
Revises: 0015_sprint30
"""
from alembic import op
import sqlalchemy as sa


revision = "0016_sprint31"
down_revision = "0015_sprint30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_deliveries",
        sa.Column("provider_status", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("provider_error_code", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notification_deliveries", "provider_updated_at")
    op.drop_column("notification_deliveries", "provider_error_code")
    op.drop_column("notification_deliveries", "provider_status")
