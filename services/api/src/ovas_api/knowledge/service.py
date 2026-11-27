"""Index and search the knowledge base. All queries are workspace-scoped (ADR-0002)."""

import asyncio
import uuid

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ovas_api.knowledge.chunking import chunk_text
from ovas_api.knowledge.embedding import get_embedder
from ovas_api.knowledge.parsing import ParseError, extract_text
from ovas_api.models import KnowledgeChunk, KnowledgeSource


class Hit(BaseModel):
    source: str
    source_id: uuid.UUID
    text: str
    score: float


async def index_source(db: AsyncSession, workspace_id: uuid.UUID, source_id: uuid.UUID) -> None:
    """Parse, chunk and embed one source; record ready or failed on the source."""
    source = await db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id, KnowledgeSource.workspace_id == workspace_id
        )
    )
    if source is None:  # deleted before the job ran
        return
    source.status, source.error = "indexing", None
    await db.commit()
    try:
        content = await db.scalar(
            select(KnowledgeSource.content).where(KnowledgeSource.id == source_id)
        )
        text = await asyncio.to_thread(extract_text, content or b"", source.mime)
        chunks = chunk_text(text)
        vectors = await asyncio.to_thread(get_embedder().passages, chunks)
    except ParseError as e:  # the file itself is unusable: no retry
        source.status, source.error, source.chunk_count = "failed", str(e), 0
        await db.commit()
        return
    except Exception as e:  # e.g. the embedding model could not load: show it, let the job retry
        await db.rollback()
        source.status, source.error = "failed", f"Indexing failed ({type(e).__name__}); retrying."
        await db.commit()
        raise
    await db.execute(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.source_id == source_id, KnowledgeChunk.workspace_id == workspace_id
        )
    )
    db.add_all(
        KnowledgeChunk(
            workspace_id=workspace_id, source_id=source_id, ordinal=i, text=t, embedding=v
        )
        for i, (t, v) in enumerate(zip(chunks, vectors, strict=True))
    )
    source.status, source.chunk_count = "ready", len(chunks)
    await db.commit()


async def search(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    query: str,
    source_ids: list[uuid.UUID],
    k: int,
) -> list[Hit]:
    """Top-k chunks by cosine similarity among the given ready sources."""
    if not query.strip() or not source_ids or k < 1:
        return []
    vector = await asyncio.to_thread(get_embedder().query, query)
    distance = KnowledgeChunk.embedding.cosine_distance(vector).label("distance")
    rows = await db.execute(
        select(KnowledgeChunk.text, KnowledgeSource.name, KnowledgeSource.id, distance)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(
            KnowledgeChunk.workspace_id == workspace_id,
            KnowledgeSource.workspace_id == workspace_id,
            KnowledgeSource.status == "ready",
            KnowledgeChunk.source_id.in_(source_ids),
        )
        .order_by(distance)
        .limit(min(k, 10))
    )
    return [
        Hit(source=name, source_id=sid, text=text, score=round(1 - float(d), 4))
        for text, name, sid, d in rows
    ]


async def knowledge_ids(db: AsyncSession, workspace_id: uuid.UUID) -> list[str]:
    """IDs of every source in the workspace, for draft validation (missing_knowledge)."""
    rows = await db.scalars(
        select(KnowledgeSource.id).where(KnowledgeSource.workspace_id == workspace_id)
    )
    return [str(i) for i in rows]
