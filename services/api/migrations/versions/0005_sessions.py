"""LLM provider settings, sessions and session events.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _workspace(index: bool = True, unique: bool = False) -> sa.Column:
    return sa.Column(
        "workspace_id",
        sa.Uuid(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=index,
        unique=unique,
    )


def upgrade() -> None:
    op.create_table(
        "llm_providers",
        *_base(),
        _workspace(index=False, unique=True),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("default_model", sa.String(200), nullable=False),
        sa.Column("reasoning_effort", sa.String(20), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
    )
    op.create_table(
        "sessions",
        *_base(),
        _workspace(),
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_number", sa.Integer(), nullable=True),
        sa.Column("draft_revision", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("end_user_id", sa.String(200), nullable=True),
        sa.Column("spec", JSONB(), nullable=False),
        sa.Column("variables", JSONB(), nullable=False),
        sa.Column("usage", JSONB(), nullable=False),
        sa.Column("outcome", sa.String(100), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "session_events",
        *_base(),
        _workspace(),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.UniqueConstraint("session_id", "seq"),
    )


def downgrade() -> None:
    op.drop_table("session_events")
    op.drop_table("sessions")
    op.drop_table("llm_providers")
