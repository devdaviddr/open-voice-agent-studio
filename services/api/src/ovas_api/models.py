"""SQLAlchemy models. Every workspace-owned table carries workspace_id (ADR-0002)."""

import os
import time
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column

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


class AgentVersion(IdMixin, Base):
    """An immutable published snapshot of a draft (MVP FR-11). A trigger rejects updates."""

    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "number"),)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    spec: Mapped[dict] = mapped_column(JSONB)


class LlmProvider(IdMixin, Base):
    """The workspace's OpenAI-compatible LLM endpoint (MVP FR-21). One per workspace."""

    __tablename__ = "llm_providers"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True
    )
    base_url: Mapped[str] = mapped_column(String(500))
    default_model: Mapped[str] = mapped_column(String(200))
    reasoning_effort: Mapped[str | None] = mapped_column(String(20), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)


class Session(IdMixin, Base):
    """One conversation with an agent, and the exact spec it ran (MVP FR-20)."""

    __tablename__ = "sessions"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draft_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(String(10), default="text")
    channel: Mapped[str] = mapped_column(String(20), default="console")
    end_user_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    spec: Mapped[dict] = mapped_column(JSONB)
    variables: Mapped[dict] = mapped_column(JSONB, default=dict)
    usage: Mapped[dict] = mapped_column(JSONB, default=dict)
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionEvent(IdMixin, Base):
    __tablename__ = "session_events"
    __table_args__ = (UniqueConstraint("session_id", "seq"),)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONB)


EMBEDDING_DIM = 384


class KnowledgeSource(IdMixin, Base):
    """An uploaded document in the workspace knowledge base (MVP FR-15)."""

    __tablename__ = "knowledge_sources"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(300))
    mime: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column("bytes", BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    # pending -> indexing -> ready | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[bytes] = deferred(mapped_column(LargeBinary))


class KnowledgeChunk(IdMixin, Base):
    __tablename__ = "knowledge_chunks"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))


class Job(IdMixin, Base):
    """Background work run by the API's in-process worker (indexing, later memory extraction)."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    # pending -> running -> done | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Memory(IdMixin, Base):
    """A durable fact about one end user of one agent (MVP FR-16)."""

    __tablename__ = "memories"
    __table_args__ = (Index("ix_memories_agent_user", "agent_id", "end_user_id"),)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    end_user_id: Mapped[str] = mapped_column(String(200))
    fact: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
