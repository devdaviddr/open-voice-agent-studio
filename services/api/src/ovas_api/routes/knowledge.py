"""Workspace knowledge base: upload, list, inspect and delete documents (MVP FR-15)."""

import hashlib
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import String, cast, select

from ovas_api import jobs
from ovas_api.auth import CurrentUser, Db
from ovas_api.knowledge.parsing import ACCEPTED, MAX_BYTES, mime_for
from ovas_api.models import Agent, AgentVersion, KnowledgeSource

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])


class KnowledgeSourceOut(BaseModel):
    id: uuid.UUID
    name: str
    mime: str
    bytes: int
    status: Literal["pending", "indexing", "ready", "failed"]
    chunks: int
    error: str | None
    created_at: datetime


def _out(s: KnowledgeSource) -> KnowledgeSourceOut:
    return KnowledgeSourceOut(
        id=s.id,
        name=s.name,
        mime=s.mime,
        bytes=s.byte_size,
        status=s.status,  # type: ignore[arg-type]
        chunks=s.chunk_count,
        error=s.error,
        created_at=s.created_at,
    )


async def _get(db: Db, principal: CurrentUser, source_id: uuid.UUID) -> KnowledgeSource:
    source = await db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.workspace_id == principal.workspace_id,
        )
    )
    if source is None:
        raise HTTPException(404, "Knowledge source not found.")
    return source


@router.get("")
async def list_sources(principal: CurrentUser, db: Db) -> list[KnowledgeSourceOut]:
    rows = await db.scalars(
        select(KnowledgeSource)
        .where(KnowledgeSource.workspace_id == principal.workspace_id)
        .order_by(KnowledgeSource.created_at.desc())
    )
    return [_out(s) for s in rows]


@router.post("", status_code=201)
async def upload(file: UploadFile, principal: CurrentUser, db: Db) -> KnowledgeSourceOut:
    name = (file.filename or "").strip()[:300]
    mime = mime_for(name)
    if not name or mime is None:
        kinds = ", ".join(sorted(ACCEPTED))
        raise HTTPException(422, f"Upload a Markdown, text or PDF file ({kinds}).")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Files must be 20 MB or smaller.")
    if not content:
        raise HTTPException(422, "The file is empty.")
    source = KnowledgeSource(
        workspace_id=principal.workspace_id,
        name=name,
        mime=mime,
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        status="pending",
        chunk_count=0,
        content=content,
    )
    db.add(source)
    await db.flush()
    jobs.enqueue(db, principal.workspace_id, "index_knowledge", {"source_id": str(source.id)})
    await db.commit()
    jobs.wake()
    return _out(source)


@router.get("/{source_id}")
async def read_source(source_id: uuid.UUID, principal: CurrentUser, db: Db) -> KnowledgeSourceOut:
    return _out(await _get(db, principal, source_id))


@router.post("/{source_id}/reindex", status_code=202)
async def reindex(source_id: uuid.UUID, principal: CurrentUser, db: Db) -> KnowledgeSourceOut:
    source = await _get(db, principal, source_id)
    source.status, source.error = "pending", None
    jobs.enqueue(db, principal.workspace_id, "index_knowledge", {"source_id": str(source.id)})
    await db.commit()
    jobs.wake()
    return _out(source)


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: uuid.UUID, principal: CurrentUser, db: Db) -> None:
    source = await _get(db, principal, source_id)
    # DD-2: a source a published version uses cannot be deleted.
    used = (
        await db.execute(
            select(Agent.name, AgentVersion.number)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                AgentVersion.workspace_id == principal.workspace_id,
                cast(AgentVersion.spec, String).contains(str(source.id)),
            )
            .order_by(Agent.name, AgentVersion.number)
        )
    ).all()
    if used:
        names = ", ".join(f"{agent} v{n}" for agent, n in used[:5])
        raise HTTPException(
            409, f"Published versions use this source ({names}). Detach it and publish first."
        )
    await db.delete(source)
    await db.commit()
