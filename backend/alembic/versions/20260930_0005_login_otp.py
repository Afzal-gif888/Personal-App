"""login OTP (EmailJS) replaces email-verification links

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-30 14:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_otps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("otp_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("send_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("window_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_login_otps_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_otps")),
    )
    op.create_index(op.f("ix_login_otps_user_id"), "login_otps", ["user_id"], unique=True)
    # The link-based verification system is gone.
    op.drop_index("ix_users_email_verification_token_hash", table_name="users")
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified_at")


def downgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verification_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_email_verification_token_hash", "users", ["email_verification_token_hash"], unique=True)
    op.drop_index(op.f("ix_login_otps_user_id"), table_name="login_otps")
    op.drop_table("login_otps")
