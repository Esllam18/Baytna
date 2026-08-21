"""Sprint 29 media, object storage and notification delivery.

Revision ID: 0014_sprint29
Revises: 0013_sprint28
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_sprint29"
down_revision = "0013_sprint28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("storage_provider", sa.String(length=30), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("expected_size_bytes", sa.Integer(), nullable=False),
        sa.Column("actual_size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("upload_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('chef_avatar','dish_image','support_attachment','delivery_proof','customer_attachment','other')",
            name="ck_media_assets_purpose",
        ),
        sa.CheckConstraint(
            "visibility IN ('private','public')",
            name="ck_media_assets_visibility",
        ),
        sa.CheckConstraint(
            "status IN ('pending','ready','failed','deleted')",
            name="ck_media_assets_status",
        ),
        sa.CheckConstraint(
            "expected_size_bytes > 0",
            name="ck_media_assets_expected_size",
        ),
        sa.CheckConstraint(
            "actual_size_bytes IS NULL OR actual_size_bytes >= 0",
            name="ck_media_assets_actual_size",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        "ix_media_assets_owner_user_id",
        "media_assets",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_media_owner_status",
        "media_assets",
        ["owner_user_id", "status", "created_at"],
    )

    op.create_table(
        "push_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_ciphertext", sa.Text(), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=True),
        sa.Column("app_version", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "platform IN ('ios','android','web')",
            name="ck_push_devices_platform",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_push_devices_user_id", "push_devices", ["user_id"])
    op.create_index(
        "ix_push_devices_user_active",
        "push_devices",
        ["user_id", "is_active", "updated_at"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), nullable=False),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False),
        sa.Column("order_updates", sa.Boolean(), nullable=False),
        sa.Column("support_updates", sa.Boolean(), nullable=False),
        sa.Column("marketing_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("target_ref", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "channel IN ('push','sms')",
            name="ck_notification_delivery_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending','processing','retry','succeeded','dead_letter','skipped')",
            name="ck_notification_delivery_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_notification_delivery_attempts",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="ck_notification_delivery_max_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "channel",
            "target_ref",
            name="uq_notification_delivery_target",
        ),
    )
    op.create_index(
        "ix_notification_deliveries_notification_id",
        "notification_deliveries",
        ["notification_id"],
    )
    op.create_index(
        "ix_notification_deliveries_user_id",
        "notification_deliveries",
        ["user_id"],
    )
    op.create_index(
        "ix_notification_deliveries_due",
        "notification_deliveries",
        ["status", "available_at", "created_at"],
    )
    op.create_index(
        "ix_notification_deliveries_user_status",
        "notification_deliveries",
        ["user_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_user_status",
        table_name="notification_deliveries",
    )
    op.drop_index(
        "ix_notification_deliveries_due",
        table_name="notification_deliveries",
    )
    op.drop_index(
        "ix_notification_deliveries_user_id",
        table_name="notification_deliveries",
    )
    op.drop_index(
        "ix_notification_deliveries_notification_id",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")
    op.drop_table("notification_preferences")

    op.drop_index(
        "ix_push_devices_user_active",
        table_name="push_devices",
    )
    op.drop_index("ix_push_devices_user_id", table_name="push_devices")
    op.drop_table("push_devices")

    op.drop_index("ix_media_owner_status", table_name="media_assets")
    op.drop_index("ix_media_assets_owner_user_id", table_name="media_assets")
    op.drop_table("media_assets")
