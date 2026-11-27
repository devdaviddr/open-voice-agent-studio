"""Long-term memories per agent and end user.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("end_user_id", sa.String(200), nullable=False),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_memories_agent_user", "memories", ["agent_id", "end_user_id"])


def downgrade() -> None:
    op.drop_index("ix_memories_agent_user", table_name="memories")
    op.drop_table("memories")
