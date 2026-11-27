"""Sessions: start one for the console, list them, read their transcript (MVP FR-17, FR-20)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from ovas_api.auth import CurrentUser, Db
from ovas_api.config import get_settings
from ovas_api.knowledge.service import knowledge_ids
from ovas_api.models import Agent, AgentVersion, Session, SessionEvent
from ovas_api.routes.agents import get_agent
from ovas_core.spec import AgentSpec
from ovas_core.tokens import sign_session
from ovas_core.validate import Issue, validate

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


class SessionStart(BaseModel):
    agent_id: uuid.UUID
    target: Literal["draft", "live"] | int = "draft"
    end_user_id: str | None = Field(default=None, max_length=200)
    variables: dict[str, Any] = {}


class SessionStarted(BaseModel):
    session_id: uuid.UUID
    stream_url: str


class SessionNotRunnable(BaseModel):
    detail: str
    issues: list[Issue] = []


class SessionSummary(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    version_number: int | None
    draft_revision: int | None
    channel: str
    end_user_id: str | None
    outcome: str | None
    turns: int
    started_at: datetime
    ended_at: datetime | None


class Event(BaseModel):
    seq: int
    type: str
    payload: dict[str, Any]
    at: datetime


class SessionDetail(SessionSummary):
    variables: dict[str, Any]
    events: list[Event]


@router.post(
    "",
    status_code=201,
    response_model=SessionStarted,
    responses={422: {"model": SessionNotRunnable}},
)
async def start_session(body: SessionStart, principal: CurrentUser, db: Db):
    agent = await get_agent(db, principal, body.agent_id)
    version_number: int | None = None
    draft_revision: int | None = None
    if body.target == "draft":
        spec = agent.draft
        draft_revision = agent.draft_revision
        known = await knowledge_ids(db, principal.workspace_id)
        issues = [
            i for i in validate(AgentSpec.model_validate(spec), known) if i.severity == "error"
        ]
        if issues:
            problem = SessionNotRunnable(
                detail="Fix the problems in the draft first.", issues=issues
            )
            return JSONResponse(problem.model_dump(), status_code=422)
    else:
        number = agent.live_version if body.target == "live" else body.target
        if number is None:
            raise HTTPException(422, "This agent has no live version yet. Publish it first.")
        version = await db.scalar(
            select(AgentVersion).where(
                AgentVersion.agent_id == agent.id, AgentVersion.number == number
            )
        )
        if version is None:
            raise HTTPException(404, f"Version {number} not found.")
        spec, version_number = version.spec, number
    session = Session(
        workspace_id=principal.workspace_id,
        agent_id=agent.id,
        version_number=version_number,
        draft_revision=draft_revision,
        mode="text",
        channel="console",
        end_user_id=body.end_user_id or None,
        spec=spec,
        variables=body.variables,
        usage={},
    )
    db.add(session)
    await db.commit()
    settings = get_settings()
    token = sign_session(str(session.id), settings.internal_key)
    return SessionStarted(
        session_id=session.id,
        stream_url=f"{settings.runtime_public_path}/v1/sessions/{session.id}/stream?token={token}",
    )


def _summary(s: Session, agent_name: str) -> SessionSummary:
    return SessionSummary(
        id=s.id,
        agent_id=s.agent_id,
        agent_name=agent_name,
        version_number=s.version_number,
        draft_revision=s.draft_revision,
        channel=s.channel,
        end_user_id=s.end_user_id,
        outcome=s.outcome,
        turns=int((s.usage or {}).get("turns", 0)),
        started_at=s.created_at,
        ended_at=s.ended_at,
    )


@router.get("")
async def list_sessions(
    principal: CurrentUser, db: Db, agent_id: uuid.UUID | None = None, limit: int = 100
) -> list[SessionSummary]:
    query = (
        select(Session, Agent.name)
        .join(Agent, Agent.id == Session.agent_id)
        .where(Session.workspace_id == principal.workspace_id)
        .order_by(Session.created_at.desc())
        .limit(min(limit, 500))
    )
    if agent_id:
        query = query.where(Session.agent_id == agent_id)
    return [_summary(s, name) for s, name in (await db.execute(query)).all()]


async def _get(db: Db, principal: CurrentUser, session_id: uuid.UUID) -> tuple[Session, str]:
    row = (
        await db.execute(
            select(Session, Agent.name)
            .join(Agent, Agent.id == Session.agent_id)
            .where(Session.id == session_id, Session.workspace_id == principal.workspace_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Session not found.")
    return row[0], row[1]


@router.get("/{session_id}")
async def read_session(session_id: uuid.UUID, principal: CurrentUser, db: Db) -> SessionDetail:
    session, name = await _get(db, principal, session_id)
    events = await db.scalars(
        select(SessionEvent).where(SessionEvent.session_id == session.id).order_by(SessionEvent.seq)
    )
    return SessionDetail(
        **_summary(session, name).model_dump(),
        variables=session.variables,
        events=[Event(seq=e.seq, type=e.type, payload=e.payload, at=e.created_at) for e in events],
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, principal: CurrentUser, db: Db) -> None:
    session, _ = await _get(db, principal, session_id)
    await db.execute(delete(Session).where(Session.id == session.id))
    await db.commit()
