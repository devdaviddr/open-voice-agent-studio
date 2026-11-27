"""Auth: workspaces, users, memberships, user sessions, login failures.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "workspaces",
        *_base(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("open_signup", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "users",
        *_base(),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
    )
    op.create_table(
        "memberships",
        *_base(),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id"),
    )
    op.create_table(
        "user_sessions",
        *_base(),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "login_failures",
        *_base(),
        sa.Column("key", sa.String(400), nullable=False),
    )
    op.create_index("ix_login_failures_key_created", "login_failures", ["key", "created_at"])


def downgrade() -> None:
    op.drop_table("login_failures")
    op.drop_table("user_sessions")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("workspaces")
