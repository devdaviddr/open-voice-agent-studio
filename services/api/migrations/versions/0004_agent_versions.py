"""Immutable agent versions.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_versions",
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
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "author_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("spec", JSONB(), nullable=False),
        sa.UniqueConstraint("agent_id", "number"),
    )
    # Versions are immutable (spec/product FR-10): reject any UPDATE at the database level.
    op.execute(
        """
        CREATE FUNCTION agent_versions_immutable() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'agent versions are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER agent_versions_no_update BEFORE UPDATE ON agent_versions "
        "FOR EACH ROW EXECUTE FUNCTION agent_versions_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS agent_versions_no_update ON agent_versions")
    op.execute("DROP FUNCTION IF EXISTS agent_versions_immutable()")
    op.drop_table("agent_versions")
