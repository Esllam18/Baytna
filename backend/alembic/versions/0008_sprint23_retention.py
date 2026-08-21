"""Sprint 23 Notifications, Favorites, Loyalty and Retention.

Revision ID: 0008_sprint23
Revises: 0007_sprint22
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_sprint23"
down_revision = "0007_sprint22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorite_chefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("chef_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chef_id"],
            ["chef_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_id",
            "chef_id",
            name="uq_favorite_chefs_customer_chef",
        ),
    )
    op.create_index(
        "ix_favorite_chefs_customer_id",
        "favorite_chefs",
        ["customer_id"],
    )
    op.create_index(
        "ix_favorite_chefs_chef_id",
        "favorite_chefs",
        ["chef_id"],
    )
    op.create_index(
        "ix_favorite_chefs_customer_created",
        "favorite_chefs",
        ["customer_id", "created_at"],
    )

    op.create_table(
        "favorite_dishes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("dish_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["dishes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_id",
            "dish_id",
            name="uq_favorite_dishes_customer_dish",
        ),
    )
    op.create_index(
        "ix_favorite_dishes_customer_id",
        "favorite_dishes",
        ["customer_id"],
    )
    op.create_index(
        "ix_favorite_dishes_dish_id",
        "favorite_dishes",
        ["dish_id"],
    )
    op.create_index(
        "ix_favorite_dishes_customer_created",
        "favorite_dishes",
        ["customer_id", "created_at"],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=180), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "dedupe_key",
            name="uq_notifications_user_dedupe_key",
        ),
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
    )
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "read_at", "created_at"],
    )

    op.create_table(
        "loyalty_accounts",
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("balance_points", sa.Integer(), nullable=False),
        sa.Column("lifetime_earned_points", sa.Integer(), nullable=False),
        sa.Column("lifetime_redeemed_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "balance_points >= 0",
            name="ck_loyalty_balance_nonnegative",
        ),
        sa.CheckConstraint(
            "lifetime_earned_points >= 0",
            name="ck_loyalty_earned_nonnegative",
        ),
        sa.CheckConstraint(
            "lifetime_redeemed_points >= 0",
            name="ck_loyalty_redeemed_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("customer_id"),
    )

    op.create_table(
        "loyalty_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("source_order_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transaction_type IN ('earn_order','redeem','adjustment')",
            name="ck_loyalty_transaction_type",
        ),
        sa.CheckConstraint(
            "points != 0",
            name="ck_loyalty_points_nonzero",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["loyalty_accounts.customer_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("source_order_id"),
    )
    op.create_index(
        "ix_loyalty_transactions_customer_id",
        "loyalty_transactions",
        ["customer_id"],
    )
    op.create_index(
        "ix_loyalty_transactions_customer_created",
        "loyalty_transactions",
        ["customer_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_loyalty_transactions_customer_created",
        table_name="loyalty_transactions",
    )
    op.drop_index(
        "ix_loyalty_transactions_customer_id",
        table_name="loyalty_transactions",
    )
    op.drop_table("loyalty_transactions")
    op.drop_table("loyalty_accounts")

    op.drop_index(
        "ix_notifications_user_unread",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_user_id",
        table_name="notifications",
    )
    op.drop_table("notifications")

    op.drop_index(
        "ix_favorite_dishes_customer_created",
        table_name="favorite_dishes",
    )
    op.drop_index(
        "ix_favorite_dishes_dish_id",
        table_name="favorite_dishes",
    )
    op.drop_index(
        "ix_favorite_dishes_customer_id",
        table_name="favorite_dishes",
    )
    op.drop_table("favorite_dishes")

    op.drop_index(
        "ix_favorite_chefs_customer_created",
        table_name="favorite_chefs",
    )
    op.drop_index(
        "ix_favorite_chefs_chef_id",
        table_name="favorite_chefs",
    )
    op.drop_index(
        "ix_favorite_chefs_customer_id",
        table_name="favorite_chefs",
    )
    op.drop_table("favorite_chefs")
