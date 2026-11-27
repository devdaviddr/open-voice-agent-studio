"""In-process background jobs backed by the `jobs` table (plan: no broker needed).

The worker claims one pending row at a time with SKIP LOCKED, so several API processes can share
the table. Rows left `running` by a crash are re-queued at start-up.
"""

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ovas_api.knowledge.service import index_source
from ovas_api.memory.service import extract_for_session
from ovas_api.models import Job

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
Handler = Callable[[AsyncSession, uuid.UUID, dict[str, Any]], Awaitable[None]]


async def _index_knowledge(db: AsyncSession, workspace_id: uuid.UUID, p: dict[str, Any]) -> None:
    await index_source(db, workspace_id, uuid.UUID(p["source_id"]))


async def _extract_memory(db: AsyncSession, workspace_id: uuid.UUID, p: dict[str, Any]) -> None:
    await extract_for_session(db, workspace_id, uuid.UUID(p["session_id"]))


HANDLERS: dict[str, Handler] = {
    "index_knowledge": _index_knowledge,
    "extract_memory": _extract_memory,
}

_wake = asyncio.Event()


def enqueue(db: AsyncSession, workspace_id: uuid.UUID, kind: str, payload: dict[str, Any]) -> Job:
    """Add a job to the session; it runs after the caller commits."""
    job = Job(workspace_id=workspace_id, kind=kind, payload=payload, status="pending")
    db.add(job)
    return job


def wake() -> None:
    _wake.set()


async def run_next(sessions: async_sessionmaker[AsyncSession]) -> bool:
    """Run one pending job. Returns False when there was nothing to do."""
    async with sessions() as db:
        job = await db.scalar(
            select(Job)
            .where(Job.status == "pending")
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False
        job.status, job.attempts = "running", job.attempts + 1
        await db.commit()
        job_id, kind, workspace_id, payload = job.id, job.kind, job.workspace_id, job.payload
    async with sessions() as db:
        try:
            await HANDLERS[kind](db, workspace_id, payload)
            status, error = "done", None
        except Exception as e:  # recorded on the job; retried up to MAX_ATTEMPTS
            log.exception("job %s (%s) failed", job_id, kind)
            await db.rollback()
            status, error = "failed", f"{type(e).__name__}: {e}"
        row = await db.get(Job, job_id)
        if row is not None:
            if status == "failed" and row.attempts < MAX_ATTEMPTS:
                status = "pending"
            row.status, row.error, row.finished_at = status, error, datetime.now(UTC)
            await db.commit()
    return True


async def run_pending(sessions: async_sessionmaker[AsyncSession]) -> int:
    """Run jobs until none are pending (tests and start-up)."""
    n = 0
    while await run_next(sessions):
        n += 1
    return n


async def worker(sessions: async_sessionmaker[AsyncSession], idle_seconds: float = 5.0) -> None:
    async with sessions() as db:
        await db.execute(update(Job).where(Job.status == "running").values(status="pending"))
        await db.commit()
    while True:
        try:
            await run_pending(sessions)
        except Exception:  # database hiccup: keep the worker alive
            log.exception("job worker loop failed")
        _wake.clear()
        with contextlib.suppress(TimeoutError):  # idle: poll again
            await asyncio.wait_for(_wake.wait(), timeout=idle_seconds)
