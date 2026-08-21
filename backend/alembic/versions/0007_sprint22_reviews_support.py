"""Sprint 22 Ratings, Reviews, Support and Post-Order Experience.

Revision ID: 0007_sprint22
Revises: 0006_sprint21
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_sprint22"
down_revision = "0006_sprint21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column("food_quality", sa.Integer(), nullable=False),
        sa.Column("packaging", sa.Integer(), nullable=False),
        sa.Column("order_accuracy", sa.Integer(), nullable=False),
        sa.Column("value_for_money", sa.Integer(), nullable=False),
        sa.Column("chef_overall", sa.Integer(), nullable=False),
        sa.Column("delivery_overall", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("moderation_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "food_quality BETWEEN 1 AND 5",
            name="ck_reviews_food_quality",
        ),
        sa.CheckConstraint(
            "packaging BETWEEN 1 AND 5",
            name="ck_reviews_packaging",
        ),
        sa.CheckConstraint(
            "order_accuracy BETWEEN 1 AND 5",
            name="ck_reviews_order_accuracy",
        ),
        sa.CheckConstraint(
            "value_for_money BETWEEN 1 AND 5",
            name="ck_reviews_value_for_money",
        ),
        sa.CheckConstraint(
            "chef_overall BETWEEN 1 AND 5",
            name="ck_reviews_chef_overall",
        ),
        sa.CheckConstraint(
            "delivery_overall IS NULL OR delivery_overall BETWEEN 1 AND 5",
            name="ck_reviews_delivery_overall",
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
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.user_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_reviews_order_id", "reviews", ["order_id"])
    op.create_index("ix_reviews_customer_id", "reviews", ["customer_id"])
    op.create_index("ix_reviews_chef_id", "reviews", ["chef_id"])
    op.create_index("ix_reviews_driver_id", "reviews", ["driver_id"])
    op.create_index(
        "ix_reviews_chef_visible",
        "reviews",
        ["chef_id", "is_visible", "created_at"],
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_admin_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("resolution_code", sa.String(length=80), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('food_quality','missing_item','wrong_item','late_delivery','delivery_issue','refund','payment','app_issue','other')",
            name="ck_support_tickets_category",
        ),
        sa.CheckConstraint(
            "priority IN ('normal','high','urgent')",
            name="ck_support_tickets_priority",
        ),
        sa.CheckConstraint(
            "status IN ('new','assigned','investigating','awaiting_customer','awaiting_internal','resolved','closed')",
            name="ck_support_tickets_status",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_tickets_customer_id",
        "support_tickets",
        ["customer_id"],
    )
    op.create_index(
        "ix_support_tickets_order_id",
        "support_tickets",
        ["order_id"],
    )
    op.create_index(
        "ix_support_tickets_assigned_admin_id",
        "support_tickets",
        ["assigned_admin_id"],
    )
    op.create_index(
        "ix_support_customer_status",
        "support_tickets",
        ["customer_id", "status", "created_at"],
    )
    op.create_index(
        "ix_support_admin_status",
        "support_tickets",
        ["assigned_admin_id", "status", "created_at"],
    )

    op.create_table(
        "support_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=True),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sender_role IN ('customer','admin','system')",
            name="ck_support_messages_sender_role",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["support_tickets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_messages_ticket_id",
        "support_messages",
        ["ticket_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_support_messages_ticket_id", table_name="support_messages")
    op.drop_table("support_messages")

    op.drop_index("ix_support_admin_status", table_name="support_tickets")
    op.drop_index("ix_support_customer_status", table_name="support_tickets")
    op.drop_index(
        "ix_support_tickets_assigned_admin_id",
        table_name="support_tickets",
    )
    op.drop_index("ix_support_tickets_order_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_customer_id", table_name="support_tickets")
    op.drop_table("support_tickets")

    op.drop_index("ix_reviews_chef_visible", table_name="reviews")
    op.drop_index("ix_reviews_driver_id", table_name="reviews")
    op.drop_index("ix_reviews_chef_id", table_name="reviews")
    op.drop_index("ix_reviews_customer_id", table_name="reviews")
    op.drop_index("ix_reviews_order_id", table_name="reviews")
    op.drop_table("reviews")
