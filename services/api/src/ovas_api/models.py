"""SQLAlchemy models. Every workspace-owned table carries workspace_id (ADR-0002)."""

import os
import time
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ovas_api.db import Base


def uuid7() -> uuid.UUID:
    """Time-ordered UUID (RFC 9562 v7): 48-bit Unix ms timestamp, then random bits."""
    ms = time.time_ns() // 1_000_000
    raw = bytearray(ms.to_bytes(6, "big") + os.urandom(10))
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw))


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(IdMixin, Base):
    __tablename__ = "workspaces"
    name: Mapped[str] = mapped_column(String(200))
    open_signup: Mapped[bool] = mapped_column(Boolean, default=True)


class User(IdMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(200), default="")


class Membership(IdMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))  # "owner" | "member"


class UserSession(IdMixin, Base):
    """A signed-in browser. The cookie holds a random token; only its SHA-256 is stored."""

    __tablename__ = "user_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginFailure(IdMixin, Base):
    """One row per failed sign-in, keyed by `email:<addr>` and `ip:<addr>` (MVP FR-3)."""

    __tablename__ = "login_failures"
    __table_args__ = (Index("ix_login_failures_key_created", "key", "created_at"),)
    key: Mapped[str] = mapped_column(String(400))


class Agent(IdMixin, Base):
    """An agent and its single editable draft (product FR-4). Versions: agent_versions."""

    __tablename__ = "agents"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    draft: Mapped[dict] = mapped_column(JSONB)
    draft_revision: Mapped[int] = mapped_column(Integer, default=1)
    live_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
