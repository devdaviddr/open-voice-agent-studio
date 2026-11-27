"""List and forget an agent's long-term memories (MVP FR-16)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select

from ovas_api.auth import CurrentUser, Db
from ovas_api.models import Memory
from ovas_api.routes.agents import get_agent

router = APIRouter(prefix="/v1/agents/{agent_id}/memories", tags=["memories"])


class MemoryOut(BaseModel):
    id: uuid.UUID
    end_user_id: str
    fact: str
    session_id: uuid.UUID | None
    created_at: datetime


@router.get("")
async def list_memories(
    agent_id: uuid.UUID,
    principal: CurrentUser,
    db: Db,
    end_user_id: Annotated[str | None, Query(max_length=200)] = None,
) -> list[MemoryOut]:
    await get_agent(db, principal, agent_id)
    stmt = select(Memory).where(
        Memory.workspace_id == principal.workspace_id, Memory.agent_id == agent_id
    )
    if end_user_id:
        stmt = stmt.where(Memory.end_user_id == end_user_id)
    rows = await db.scalars(stmt.order_by(Memory.end_user_id, Memory.created_at))
    return [
        MemoryOut(
            id=m.id,
            end_user_id=m.end_user_id,
            fact=m.fact,
            session_id=m.session_id,
            created_at=m.created_at,
        )
        for m in rows
    ]


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    agent_id: uuid.UUID, memory_id: uuid.UUID, principal: CurrentUser, db: Db
) -> None:
    await get_agent(db, principal, agent_id)
    result = await db.execute(
        delete(Memory).where(
            Memory.id == memory_id,
            Memory.agent_id == agent_id,
            Memory.workspace_id == principal.workspace_id,
        )
    )
    if not result.rowcount:  # type: ignore[attr-defined]
        raise HTTPException(404, "Memory not found.")
    await db.commit()


@router.delete("", status_code=204)
async def forget_end_user(
    agent_id: uuid.UUID,
    principal: CurrentUser,
    db: Db,
    end_user_id: Annotated[str, Query(min_length=1, max_length=200)],
) -> None:
    """Forget everything this agent remembers about one end user."""
    await get_agent(db, principal, agent_id)
    await db.execute(
        delete(Memory).where(
            Memory.workspace_id == principal.workspace_id,
            Memory.agent_id == agent_id,
            Memory.end_user_id == end_user_id,
        )
    )
    await db.commit()
