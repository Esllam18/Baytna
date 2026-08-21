"""Sprint 32 Paymob gateway and payment reconciliation.

Revision ID: 0017_sprint32
Revises: 0016_sprint31
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_sprint32"
down_revision = "0016_sprint31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("provider_order_reference", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("provider_transaction_reference", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("provider_status", sa.String(length=60), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("provider_last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "refunds",
        sa.Column("provider_status", sa.String(length=60), nullable=True),
    )
    op.add_column(
        "refunds",
        sa.Column("provider_error", sa.Text(), nullable=True),
    )

    op.create_table(
        "payment_provider_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_transaction_id", sa.String(length=180), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("provider_order_reference", sa.String(length=180), nullable=True),
        sa.Column("parent_provider_transaction_id", sa.String(length=180), nullable=True),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("pending", sa.Boolean(), nullable=False),
        sa.Column("is_refunded", sa.Boolean(), nullable=False),
        sa.Column("refunded_minor", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transaction_type IN ('payment','refund','void')",
            name="ck_payment_provider_transaction_type",
        ),
        sa.CheckConstraint(
            "amount_minor >= 0",
            name="ck_payment_provider_transaction_amount",
        ),
        sa.CheckConstraint(
            "refunded_minor >= 0",
            name="ck_payment_provider_transaction_refunded",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_transaction_id",
            name="uq_payment_provider_transaction",
        ),
    )
    op.create_index(
        "ix_payment_provider_transactions_payment_id",
        "payment_provider_transactions",
        ["payment_id"],
    )
    op.create_index(
        "ix_payment_provider_tx_payment",
        "payment_provider_transactions",
        ["payment_id", "observed_at"],
    )
    op.create_index(
        "ix_payment_provider_tx_order_ref",
        "payment_provider_transactions",
        ["provider", "provider_order_reference"],
    )

    op.create_table(
        "payment_reconciliation_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=220), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("provider_transaction_id", sa.String(length=180), nullable=True),
        sa.Column("issue_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expected_json", sa.JSON(), nullable=False),
        sa.Column("actual_json", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "issue_type IN ('unmatched_provider_transaction','amount_mismatch','currency_mismatch','status_mismatch','refund_mismatch')",
            name="ck_payment_reconciliation_issue_type",
        ),
        sa.CheckConstraint(
            "status IN ('open','resolved')",
            name="ck_payment_reconciliation_issue_status",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index(
        "ix_payment_reconciliation_issues_payment_id",
        "payment_reconciliation_issues",
        ["payment_id"],
    )
    op.create_index(
        "ix_payment_reconciliation_open",
        "payment_reconciliation_issues",
        ["status", "issue_type", "last_detected_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_reconciliation_open",
        table_name="payment_reconciliation_issues",
    )
    op.drop_index(
        "ix_payment_reconciliation_issues_payment_id",
        table_name="payment_reconciliation_issues",
    )
    op.drop_table("payment_reconciliation_issues")

    op.drop_index(
        "ix_payment_provider_tx_order_ref",
        table_name="payment_provider_transactions",
    )
    op.drop_index(
        "ix_payment_provider_tx_payment",
        table_name="payment_provider_transactions",
    )
    op.drop_index(
        "ix_payment_provider_transactions_payment_id",
        table_name="payment_provider_transactions",
    )
    op.drop_table("payment_provider_transactions")

    op.drop_column("refunds", "provider_error")
    op.drop_column("refunds", "provider_status")

    op.drop_column("payments", "provider_last_seen_at")
    op.drop_column("payments", "provider_status")
    op.drop_column("payments", "provider_transaction_reference")
    op.drop_column("payments", "provider_order_reference")
