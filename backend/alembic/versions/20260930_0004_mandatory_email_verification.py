"""mandatory email verification: hashed single-use tokens

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-30 10:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verification_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_email_verification_token_hash", "users", ["email_verification_token_hash"], unique=True)
    # 0003 marked pre-existing accounts verified by copying created_at, without any proof that the
    # user owns the address. Undo exactly those, unless the user has since proved ownership (clicked
    # a verification link, or reset their password through an emailed link).
    op.execute(
        """
        UPDATE users SET email_verified_at = NULL
        WHERE email_verified_at = created_at
          AND NOT EXISTS (
            SELECT 1 FROM audit_logs a
            WHERE a.user_id = users.id AND a.action IN ('auth.email_verified', 'auth.password_reset')
          )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_email_verification_token_hash", table_name="users")
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
