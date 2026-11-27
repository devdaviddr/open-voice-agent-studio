"""Agents and their drafts (MVP FR-4, FR-7, FR-8)."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from ovas_api.auth import CurrentUser, Db
from ovas_api.models import Agent
from ovas_core.spec import AgentSpec
from ovas_core.templates import TEMPLATES
from ovas_core.validate import Issue, validate

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class AgentSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    draft_revision: int
    live_version: int | None
    node_count: int
    updated_at: datetime


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    template: Literal["blank", "receptionist"] = "blank"


class AgentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class Draft(BaseModel):
    revision: int
    spec: AgentSpec


class DraftConflict(BaseModel):
    detail: str
    current_revision: int


class Validation(BaseModel):
    issues: list[Issue]


def summary(agent: Agent) -> AgentSummary:
    return AgentSummary(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        draft_revision=agent.draft_revision,
        live_version=agent.live_version,
        node_count=len(agent.draft.get("graph", {}).get("nodes", [])),
        updated_at=agent.updated_at,
    )


async def get_agent(db: Db, principal: CurrentUser, agent_id: uuid.UUID) -> Agent:
    agent = await db.scalar(
        select(Agent).where(Agent.id == agent_id, Agent.workspace_id == principal.workspace_id)
    )
    if agent is None:
        raise HTTPException(404, "Agent not found.")
    return agent


@router.get("")
async def list_agents(principal: CurrentUser, db: Db) -> list[AgentSummary]:
    rows = await db.scalars(
        select(Agent)
        .where(Agent.workspace_id == principal.workspace_id)
        .order_by(Agent.updated_at.desc())
    )
    return [summary(a) for a in rows]


@router.post("", status_code=201)
async def create_agent(body: AgentCreate, principal: CurrentUser, db: Db) -> AgentSummary:
    spec = TEMPLATES[body.template]()
    agent = Agent(
        workspace_id=principal.workspace_id,
        name=body.name,
        description=body.description,
        draft=spec.model_dump(mode="json"),
        draft_revision=1,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return summary(agent)


@router.get("/{agent_id}")
async def read_agent(agent_id: uuid.UUID, principal: CurrentUser, db: Db) -> AgentSummary:
    return summary(await get_agent(db, principal, agent_id))


@router.patch("/{agent_id}")
async def patch_agent(
    agent_id: uuid.UUID, body: AgentPatch, principal: CurrentUser, db: Db
) -> AgentSummary:
    agent = await get_agent(db, principal, agent_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return summary(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: uuid.UUID, principal: CurrentUser, db: Db) -> None:
    await db.delete(await get_agent(db, principal, agent_id))
    await db.commit()


@router.post("/{agent_id}/duplicate", status_code=201)
async def duplicate_agent(agent_id: uuid.UUID, principal: CurrentUser, db: Db) -> AgentSummary:
    source = await get_agent(db, principal, agent_id)
    copy = Agent(
        workspace_id=principal.workspace_id,
        name=f"Copy of {source.name}"[:120],
        description=source.description,
        draft=source.draft,
        draft_revision=1,
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return summary(copy)


@router.get("/{agent_id}/draft")
async def read_draft(agent_id: uuid.UUID, principal: CurrentUser, db: Db) -> Draft:
    agent = await get_agent(db, principal, agent_id)
    return Draft(revision=agent.draft_revision, spec=AgentSpec.model_validate(agent.draft))


@router.put("/{agent_id}/draft", response_model=Draft, responses={409: {"model": DraftConflict}})
async def save_draft(agent_id: uuid.UUID, body: Draft, principal: CurrentUser, db: Db):
    """Save the draft if `revision` is still current; otherwise 409 with the current revision."""
    new_revision = await db.scalar(
        update(Agent)
        .where(
            Agent.id == agent_id,
            Agent.workspace_id == principal.workspace_id,
            Agent.draft_revision == body.revision,
        )
        .values(draft=body.spec.model_dump(mode="json"), draft_revision=Agent.draft_revision + 1)
        .returning(Agent.draft_revision)
    )
    if new_revision is None:
        agent = await get_agent(db, principal, agent_id)  # 404 if it is not ours
        conflict = DraftConflict(
            detail="This agent was saved somewhere else since you opened it.",
            current_revision=agent.draft_revision,
        )
        return JSONResponse(conflict.model_dump(), status_code=409)
    await db.commit()
    return Draft(revision=new_revision, spec=body.spec)


@router.post("/{agent_id}/validate")
async def validate_spec(
    agent_id: uuid.UUID, spec: AgentSpec, principal: CurrentUser, db: Db
) -> Validation:
    await get_agent(db, principal, agent_id)
    return Validation(issues=validate(spec))
