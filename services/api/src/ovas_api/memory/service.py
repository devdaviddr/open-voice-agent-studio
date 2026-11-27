"""Store, recall and forget memories. Every query is scoped by workspace (ADR-0002)."""

import asyncio
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ovas_api.knowledge.embedding import get_embedder
from ovas_api.memory.extract import extract_facts
from ovas_api.models import Memory, Session, SessionEvent
from ovas_api.routes.llm import resolve_llm

RECALL_AT_START = 5
DUPLICATE_SIMILARITY = 0.9
TRANSCRIPT_TYPES = {"user_message": "Caller", "assistant_message": "Agent"}


def wants_memory(session: Session) -> bool:
    """Memory runs only for agents with memory on and a known end user."""
    enabled = bool((session.spec.get("memory") or {}).get("enabled"))
    return enabled and bool(session.end_user_id)


async def _transcript(db: AsyncSession, session: Session) -> str:
    events = await db.scalars(
        select(SessionEvent)
        .where(
            SessionEvent.session_id == session.id,
            SessionEvent.workspace_id == session.workspace_id,
            SessionEvent.type.in_(TRANSCRIPT_TYPES),
        )
        .order_by(SessionEvent.seq)
    )
    return "\n".join(f"{TRANSCRIPT_TYPES[e.type]}: {e.payload.get('text', '')}" for e in events)


def _scope(session: Session):
    return (
        Memory.workspace_id == session.workspace_id,
        Memory.agent_id == session.agent_id,
        Memory.end_user_id == session.end_user_id,
    )


async def extract_for_session(
    db: AsyncSession, workspace_id: uuid.UUID, session_id: uuid.UUID
) -> None:
    """Job handler: turn a finished conversation into new, de-duplicated memories."""
    session = await db.scalar(
        select(Session).where(Session.id == session_id, Session.workspace_id == workspace_id)
    )
    if session is None or not wants_memory(session):
        return
    transcript = await _transcript(db, session)
    if "Caller:" not in transcript:
        return
    known = list(
        await db.scalars(select(Memory.fact).where(*_scope(session)).order_by(Memory.created_at))
    )
    facts = await extract_facts(await resolve_llm(db, workspace_id), transcript, known[-50:])
    if not facts:
        return
    vectors = await asyncio.to_thread(get_embedder().passages, facts)
    saved: list[str] = []
    for fact, vector in zip(facts, vectors, strict=True):
        distance = await db.scalar(
            select(func.min(Memory.embedding.cosine_distance(vector))).where(*_scope(session))
        )
        if distance is not None and 1 - float(distance) >= DUPLICATE_SIMILARITY:
            continue
        db.add(
            Memory(
                workspace_id=workspace_id,
                agent_id=session.agent_id,
                end_user_id=session.end_user_id,
                fact=fact,
                embedding=vector,
                session_id=session.id,
            )
        )
        await db.flush()  # later facts are compared with this one too
        saved.append(fact)
    if saved:
        seq = await db.scalar(
            select(func.coalesce(func.max(SessionEvent.seq), 0)).where(
                SessionEvent.session_id == session.id
            )
        )
        db.add(
            SessionEvent(
                workspace_id=workspace_id,
                session_id=session.id,
                seq=(seq or 0) + 1,
                type="memory_saved",
                payload={"facts": saved},
            )
        )
    await db.commit()


async def recall(db: AsyncSession, session: Session, query: str, k: int) -> list[str]:
    """Most recent facts for an empty query (session start), else the closest by meaning."""
    if not wants_memory(session):
        return []
    stmt = select(Memory.fact).where(*_scope(session))
    if query.strip():
        vector = await asyncio.to_thread(get_embedder().query, query)
        stmt = stmt.order_by(Memory.embedding.cosine_distance(vector))
    else:
        stmt = stmt.order_by(Memory.created_at.desc())
    return list(await db.scalars(stmt.limit(min(k, 10))))
