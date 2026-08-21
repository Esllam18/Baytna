"""Sprint 25 Admin Operations Dashboard, Analytics and Reporting.
Revision ID: 0010_sprint25
Revises: 0009_sprint24
"""
from alembic import op
import sqlalchemy as sa
revision="0010_sprint25"; down_revision="0009_sprint24"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table(
        "admin_order_notes",
        sa.Column("id",sa.Uuid(),nullable=False),
        sa.Column("order_id",sa.Uuid(),nullable=False),
        sa.Column("admin_user_id",sa.Uuid(),nullable=True),
        sa.Column("note",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"],["users.id"],ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"],["orders.id"],ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_order_notes_order_id","admin_order_notes",["order_id"])
    op.create_index("ix_admin_order_notes_admin_user_id","admin_order_notes",["admin_user_id"])
    op.create_index("ix_admin_order_notes_order_created","admin_order_notes",["order_id","created_at"])
    op.create_index("ix_orders_status_created_reporting","orders",["status","created_at"])
    op.create_index("ix_payments_status_created_reporting","payments",["status","created_at"])
    op.create_index("ix_refunds_status_created_reporting","refunds",["status","created_at"])
    op.create_index("ix_support_status_created_reporting","support_tickets",["status","created_at"])
    op.create_index("ix_delivery_status_created_reporting","delivery_tasks",["status","created_at"])

def downgrade():
    op.drop_index("ix_delivery_status_created_reporting",table_name="delivery_tasks")
    op.drop_index("ix_support_status_created_reporting",table_name="support_tickets")
    op.drop_index("ix_refunds_status_created_reporting",table_name="refunds")
    op.drop_index("ix_payments_status_created_reporting",table_name="payments")
    op.drop_index("ix_orders_status_created_reporting",table_name="orders")
    op.drop_index("ix_admin_order_notes_order_created",table_name="admin_order_notes")
    op.drop_index("ix_admin_order_notes_admin_user_id",table_name="admin_order_notes")
    op.drop_index("ix_admin_order_notes_order_id",table_name="admin_order_notes")
    op.drop_table("admin_order_notes")
