"""Publishing, versions, the live pointer and diffs (MVP FR-11, FR-12)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from ovas_api.auth import CurrentUser, Db
from ovas_api.knowledge.service import knowledge_ids
from ovas_api.models import Agent, AgentVersion, User
from ovas_api.routes.agents import Draft, get_agent
from ovas_core.diff import Change, diff
from ovas_core.spec import AgentSpec
from ovas_core.validate import Issue, validate

router = APIRouter(prefix="/v1/agents/{agent_id}", tags=["versions"])


class VersionSummary(BaseModel):
    number: int
    message: str
    author: str | None
    created_at: datetime
    is_live: bool


class Version(VersionSummary):
    spec: AgentSpec


class Publish(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class PublishRejected(BaseModel):
    detail: str
    issues: list[Issue]


class LivePointer(BaseModel):
    version: int


class Diff(BaseModel):
    source: str
    target: str
    changes: list[Change]


async def _rows(db: Db, agent: Agent, number: int | None = None):
    query = (
        select(AgentVersion, User.display_name, User.email)
        .outerjoin(User, User.id == AgentVersion.author_id)
        .where(AgentVersion.agent_id == agent.id, AgentVersion.workspace_id == agent.workspace_id)
        .order_by(AgentVersion.number.desc())
    )
    if number is not None:
        query = query.where(AgentVersion.number == number)
    return (await db.execute(query)).all()


def _summary(row, live: int | None) -> VersionSummary:
    v, name, email = row
    return VersionSummary(
        number=v.number,
        message=v.message,
        author=name or email,
        created_at=v.created_at,
        is_live=v.number == live,
    )


async def _spec(db: Db, agent: Agent, ref: str) -> AgentSpec:
    if ref == "draft":
        return AgentSpec.model_validate(agent.draft)
    if not ref.isdigit():
        raise HTTPException(422, "Use 'draft' or a version number.")
    rows = await _rows(db, agent, int(ref))
    if not rows:
        raise HTTPException(404, f"Version {ref} not found.")
    return AgentSpec.model_validate(rows[0][0].spec)


@router.post(
    "/versions",
    status_code=201,
    response_model=VersionSummary,
    responses={422: {"model": PublishRejected}},
)
async def publish(agent_id: uuid.UUID, body: Publish, principal: CurrentUser, db: Db):
    agent = await get_agent(db, principal, agent_id)
    spec = AgentSpec.model_validate(agent.draft)
    known = await knowledge_ids(db, principal.workspace_id)
    issues = [i for i in validate(spec, known) if i.severity == "error"]
    if issues:
        rejected = PublishRejected(
            detail="Fix the problems in the draft before publishing.", issues=issues
        )
        return JSONResponse(rejected.model_dump(), status_code=422)
    # Lock the agent row so two publishes cannot take the same number.
    await db.execute(select(Agent.id).where(Agent.id == agent.id).with_for_update())
    number = (
        await db.scalar(
            select(func.max(AgentVersion.number)).where(AgentVersion.agent_id == agent.id)
        )
        or 0
    ) + 1
    version = AgentVersion(
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
        number=number,
        message=body.message,
        author_id=principal.user.id,
        spec=agent.draft,
    )
    db.add(version)
    agent.live_version = number
    await db.commit()
    return VersionSummary(
        number=number,
        message=body.message,
        author=principal.user.display_name or principal.user.email,
        created_at=version.created_at,
        is_live=True,
    )


@router.get("/versions")
async def list_versions(
    agent_id: uuid.UUID, principal: CurrentUser, db: Db
) -> list[VersionSummary]:
    agent = await get_agent(db, principal, agent_id)
    return [_summary(r, agent.live_version) for r in await _rows(db, agent)]


@router.get("/versions/{number}")
async def read_version(agent_id: uuid.UUID, number: int, principal: CurrentUser, db: Db) -> Version:
    agent = await get_agent(db, principal, agent_id)
    rows = await _rows(db, agent, number)
    if not rows:
        raise HTTPException(404, f"Version {number} not found.")
    summary = _summary(rows[0], agent.live_version)
    return Version(**summary.model_dump(), spec=AgentSpec.model_validate(rows[0][0].spec))


@router.post("/versions/{number}/restore")
async def restore(agent_id: uuid.UUID, number: int, principal: CurrentUser, db: Db) -> Draft:
    """Copy a version into the draft. Bumps the revision, so open builders see a conflict."""
    agent = await get_agent(db, principal, agent_id)
    spec = await _spec(db, agent, str(number))
    revision = await db.scalar(
        update(Agent)
        .where(Agent.id == agent.id)
        .values(draft=spec.model_dump(mode="json"), draft_revision=Agent.draft_revision + 1)
        .returning(Agent.draft_revision)
    )
    await db.commit()
    assert revision is not None
    return Draft(revision=revision, spec=spec)


@router.put("/live")
async def set_live(
    agent_id: uuid.UUID, body: LivePointer, principal: CurrentUser, db: Db
) -> VersionSummary:
    agent = await get_agent(db, principal, agent_id)
    rows = await _rows(db, agent, body.version)
    if not rows:
        raise HTTPException(404, f"Version {body.version} not found.")
    agent.live_version = body.version
    await db.commit()
    return _summary(rows[0], body.version)


@router.get("/diff")
async def diff_specs(
    agent_id: uuid.UUID,
    principal: CurrentUser,
    db: Db,
    source: Annotated[str, Query(alias="from", description="'draft' or a version number")],
    target: Annotated[str, Query(alias="to", description="'draft' or a version number")] = "draft",
) -> Diff:
    agent = await get_agent(db, principal, agent_id)
    changes = diff(await _spec(db, agent, source), await _spec(db, agent, target))
    return Diff(source=source, target=target, changes=changes)
