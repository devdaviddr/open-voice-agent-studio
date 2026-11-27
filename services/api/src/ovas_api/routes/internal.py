"""Endpoints for the runtime only, guarded by OVAS_INTERNAL_KEY (never called by browsers)."""

import hmac
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ovas_api.auth import Db
from ovas_api.config import get_settings
from ovas_api.knowledge.service import Hit, search
from ovas_api.models import Session, SessionEvent
from ovas_api.routes.llm import ResolvedLlm, resolve_llm


def require_internal_key(x_internal_key: Annotated[str | None, Header()] = None) -> None:
    if not x_internal_key or not hmac.compare_digest(x_internal_key, get_settings().internal_key):
        raise HTTPException(403, "Internal endpoint.")


router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_key)]
)


class RuntimeSession(BaseModel):
    session_id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    spec: dict[str, Any]
    variables: dict[str, Any]
    end_user_id: str | None
    ended: bool
    llm: ResolvedLlm


class EventIn(BaseModel):
    type: str
    payload: dict[str, Any]


class SessionEnd(BaseModel):
    outcome: str | None
    variables: dict[str, Any]
    usage: dict[str, Any]


async def _session(db: Db, session_id: uuid.UUID) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(404, "Session not found.")
    return session


@router.get("/sessions/{session_id}")
async def runtime_session(session_id: uuid.UUID, db: Db) -> RuntimeSession:
    s = await _session(db, session_id)
    return RuntimeSession(
        session_id=s.id,
        workspace_id=s.workspace_id,
        agent_id=s.agent_id,
        spec=s.spec,
        variables=s.variables,
        end_user_id=s.end_user_id,
        ended=s.ended_at is not None,
        llm=await resolve_llm(db, s.workspace_id),
    )


@router.post("/sessions/{session_id}/events", status_code=204)
async def append_events(session_id: uuid.UUID, events: list[EventIn], db: Db) -> None:
    s = await _session(db, session_id)
    await db.execute(select(Session.id).where(Session.id == s.id).with_for_update())
    seq = await db.scalar(
        select(func.coalesce(func.max(SessionEvent.seq), 0)).where(SessionEvent.session_id == s.id)
    )
    for i, e in enumerate(events, start=(seq or 0) + 1):
        db.add(
            SessionEvent(
                workspace_id=s.workspace_id, session_id=s.id, seq=i, type=e.type, payload=e.payload
            )
        )
    await db.commit()


@router.post("/sessions/{session_id}/end", status_code=204)
async def end_session(session_id: uuid.UUID, body: SessionEnd, db: Db) -> None:
    s = await _session(db, session_id)
    if s.ended_at is None:
        s.ended_at = datetime.now(UTC)
        s.outcome = body.outcome
        s.variables = body.variables
        s.usage = body.usage
        await db.commit()


class KnowledgeQuery(BaseModel):
    query: str = Field(max_length=2000)
    source_ids: list[str] | None = None  # null = every source attached to the agent
    k: int = Field(default=4, ge=1, le=10)


@router.post("/sessions/{session_id}/knowledge/search")
async def search_knowledge(session_id: uuid.UUID, body: KnowledgeQuery, db: Db) -> list[Hit]:
    """Search only the sources attached to the session's agent, in its workspace (MVP FR-15)."""
    s = await _session(db, session_id)
    attached = {r.get("source_id") for r in s.spec.get("knowledge", [])}
    wanted = attached if body.source_ids is None else attached & set(body.source_ids)
    ids: list[uuid.UUID] = []
    for raw in wanted:
        try:
            ids.append(uuid.UUID(str(raw)))
        except ValueError:
            continue
    return await search(db, s.workspace_id, body.query, ids, body.k)
