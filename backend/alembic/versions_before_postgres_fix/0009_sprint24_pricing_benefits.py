"""Sprint 24 Coupons, Loyalty Redemption, Subscriptions and Pricing Rules.

Revision ID: 0009_sprint24
Revises: 0008_sprint23
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_sprint24"
down_revision = "0008_sprint23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column("min_subtotal_minor", sa.Integer(), nullable=False),
        sa.Column("max_discount_minor", sa.Integer(), nullable=True),
        sa.Column("total_usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_customer_usage_limit", sa.Integer(), nullable=False),
        sa.Column("reserved_count", sa.Integer(), nullable=False),
        sa.Column("redeemed_count", sa.Integer(), nullable=False),
        sa.Column("stack_with_subscription", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("discount_type IN ('fixed','percent')", name="ck_coupons_discount_type"),
        sa.CheckConstraint("discount_value > 0", name="ck_coupons_discount_value"),
        sa.CheckConstraint("min_subtotal_minor >= 0", name="ck_coupons_min_subtotal"),
        sa.CheckConstraint("max_discount_minor IS NULL OR max_discount_minor > 0", name="ck_coupons_max_discount"),
        sa.CheckConstraint("total_usage_limit IS NULL OR total_usage_limit > 0", name="ck_coupons_total_limit"),
        sa.CheckConstraint("per_customer_usage_limit > 0", name="ck_coupons_customer_limit"),
        sa.CheckConstraint("reserved_count >= 0", name="ck_coupons_reserved_nonnegative"),
        sa.CheckConstraint("redeemed_count >= 0", name="ck_coupons_redeemed_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"])

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coupon_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("discount_minor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=100), nullable=True),
        sa.CheckConstraint("discount_minor > 0", name="ck_coupon_redemptions_discount"),
        sa.CheckConstraint("status IN ('reserved','applied','released')", name="ck_coupon_redemptions_status"),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions", ["coupon_id"])
    op.create_index("ix_coupon_redemptions_customer_id", "coupon_redemptions", ["customer_id"])
    op.create_index("ix_coupon_redemptions_order_id", "coupon_redemptions", ["order_id"])
    op.create_index("ix_coupon_redemptions_coupon_status", "coupon_redemptions", ["coupon_id", "status"])
    op.create_index("ix_coupon_redemptions_customer_coupon", "coupon_redemptions", ["customer_id", "coupon_id"])

    op.create_table(
        "loyalty_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("discount_minor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=100), nullable=True),
        sa.CheckConstraint("points > 0", name="ck_loyalty_redemptions_points"),
        sa.CheckConstraint("discount_minor > 0", name="ck_loyalty_redemptions_discount"),
        sa.CheckConstraint("status IN ('reserved','applied','released')", name="ck_loyalty_redemptions_status"),
        sa.ForeignKeyConstraint(["customer_id"], ["loyalty_accounts.customer_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_loyalty_redemptions_customer_id", "loyalty_redemptions", ["customer_id"])
    op.create_index("ix_loyalty_redemptions_order_id", "loyalty_redemptions", ["order_id"])
    op.create_index("ix_loyalty_redemptions_customer_status", "loyalty_redemptions", ["customer_id", "status"])

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("order_discount_bps", sa.Integer(), nullable=False),
        sa.Column("max_order_discount_minor", sa.Integer(), nullable=True),
        sa.Column("loyalty_multiplier_bps", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price_minor >= 0", name="ck_subscription_plans_price"),
        sa.CheckConstraint("duration_days > 0", name="ck_subscription_plans_duration"),
        sa.CheckConstraint("order_discount_bps BETWEEN 0 AND 10000", name="ck_subscription_plans_order_discount"),
        sa.CheckConstraint("max_order_discount_minor IS NULL OR max_order_discount_minor > 0", name="ck_subscription_plans_max_discount"),
        sa.CheckConstraint("loyalty_multiplier_bps >= 10000", name="ck_subscription_plans_loyalty_multiplier"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"])

    op.create_table(
        "customer_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active','cancelled','expired')", name="ck_customer_subscriptions_status"),
        sa.CheckConstraint("source IN ('manual','promo','billing')", name="ck_customer_subscriptions_source"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_subscriptions_customer_id", "customer_subscriptions", ["customer_id"])
    op.create_index("ix_customer_subscriptions_plan_id", "customer_subscriptions", ["plan_id"])
    op.create_index("ix_customer_subscriptions_customer_status", "customer_subscriptions", ["customer_id", "status", "ends_at"])

    op.create_table(
        "order_pricing_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("adjustment_type", sa.String(length=30), nullable=False),
        sa.Column("reference_code", sa.String(length=80), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("adjustment_type IN ('coupon','loyalty','subscription')", name="ck_order_pricing_adjustment_type"),
        sa.CheckConstraint("amount_minor >= 0", name="ck_order_pricing_adjustment_amount"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "adjustment_type", name="uq_order_pricing_adjustment_type"),
    )
    op.create_index("ix_order_pricing_adjustments_order_id", "order_pricing_adjustments", ["order_id"])
    op.create_index("ix_order_pricing_adjustments_order", "order_pricing_adjustments", ["order_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_order_pricing_adjustments_order", table_name="order_pricing_adjustments")
    op.drop_index("ix_order_pricing_adjustments_order_id", table_name="order_pricing_adjustments")
    op.drop_table("order_pricing_adjustments")

    op.drop_index("ix_customer_subscriptions_customer_status", table_name="customer_subscriptions")
    op.drop_index("ix_customer_subscriptions_plan_id", table_name="customer_subscriptions")
    op.drop_index("ix_customer_subscriptions_customer_id", table_name="customer_subscriptions")
    op.drop_table("customer_subscriptions")

    op.drop_index("ix_subscription_plans_code", table_name="subscription_plans")
    op.drop_table("subscription_plans")

    op.drop_index("ix_loyalty_redemptions_customer_status", table_name="loyalty_redemptions")
    op.drop_index("ix_loyalty_redemptions_order_id", table_name="loyalty_redemptions")
    op.drop_index("ix_loyalty_redemptions_customer_id", table_name="loyalty_redemptions")
    op.drop_table("loyalty_redemptions")

    op.drop_index("ix_coupon_redemptions_customer_coupon", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_status", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_order_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_customer_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")

    op.drop_index("ix_coupons_code", table_name="coupons")
    op.drop_table("coupons")
