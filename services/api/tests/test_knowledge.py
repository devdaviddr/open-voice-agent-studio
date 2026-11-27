import pytest

from ovas_api import jobs
from ovas_api.db import get_sessionmaker
from ovas_api.knowledge.chunking import chunk_text
from ovas_api.knowledge.embedding import HashEmbedder, set_embedder
from ovas_api.models import KnowledgeSource, Workspace

from .test_sessions import internal_headers, new_agent

HANDBOOK = b"""# Bright Smile Dental handbook

## Opening hours
We are open Monday to Friday, 8am to 6pm, and Saturday mornings 9am to noon.

## Prices
A standard cleaning costs 145 dollars. Whitening costs 390 dollars.
"""

OTHER = b"# Car park\nParking is free behind the building for two hours."


@pytest.fixture(autouse=True)
def fake_embedder():
    set_embedder(HashEmbedder())
    yield
    set_embedder(None)


async def upload(c, name: str, content: bytes, mime: str = "text/markdown") -> dict:
    res = await c.post("/v1/knowledge", files={"file": (name, content, mime)})
    assert res.status_code == 201, res.text
    return res.json()


async def index_all() -> None:
    await jobs.run_pending(get_sessionmaker())


async def attach(c, agent_id: str, source_ids: list[str]) -> None:
    draft = (await c.get(f"/v1/agents/{agent_id}/draft")).json()
    draft["spec"]["knowledge"] = [{"source_id": s} for s in source_ids]
    res = await c.put(f"/v1/agents/{agent_id}/draft", json=draft)
    assert res.status_code == 200, res.text


async def test_markdown_upload_is_indexed_and_searchable(owner):  # MVP AC-14
    source = await upload(owner, "handbook.md", HANDBOOK)
    assert source["status"] == "pending" and source["bytes"] == len(HANDBOOK)
    await index_all()
    ready = (await owner.get(f"/v1/knowledge/{source['id']}")).json()
    assert ready["status"] == "ready" and ready["chunks"] == 2 and ready["error"] is None

    other = await upload(owner, "parking.md", OTHER)
    await index_all()
    agent_id = await new_agent(owner)
    await attach(owner, agent_id, [source["id"]])
    sid = (await owner.post("/v1/sessions", json={"agent_id": agent_id})).json()["session_id"]

    hits = (
        await owner.post(
            f"/internal/sessions/{sid}/knowledge/search",
            json={"query": "How much does a cleaning cost?", "k": 2},
            headers=internal_headers(),
        )
    ).json()
    assert hits[0]["source"] == "handbook.md"
    assert "145 dollars" in hits[0]["text"] and hits[0]["text"].startswith("Bright Smile")
    # Only sources attached to the agent are searched.
    assert all(h["source_id"] != other["id"] for h in hits)
    narrowed = await owner.post(
        f"/internal/sessions/{sid}/knowledge/search",
        json={"query": "parking", "source_ids": [other["id"]]},
        headers=internal_headers(),
    )
    assert narrowed.json() == []


async def test_search_requires_internal_key(owner):
    agent_id = await new_agent(owner)
    sid = (await owner.post("/v1/sessions", json={"agent_id": agent_id})).json()["session_id"]
    res = await owner.post(f"/internal/sessions/{sid}/knowledge/search", json={"query": "x"})
    assert res.status_code == 403


async def test_sources_are_workspace_scoped(owner):  # ADR-0002
    async with get_sessionmaker()() as db:
        other = Workspace(name="Other")
        db.add(other)
        await db.flush()
        foreign = KnowledgeSource(
            workspace_id=other.id,
            name="secret.md",
            mime="text/markdown",
            byte_size=6,
            sha256="0" * 64,
            status="pending",
            chunk_count=0,
            content=b"# Secret prices",
        )
        db.add(foreign)
        await db.commit()
        foreign_id = str(foreign.id)
    await index_all()  # indexes it in its own workspace
    assert (await owner.get(f"/v1/knowledge/{foreign_id}")).status_code == 404
    assert (await owner.delete(f"/v1/knowledge/{foreign_id}")).status_code == 404
    assert foreign_id not in [s["id"] for s in (await owner.get("/v1/knowledge")).json()]
    # Even if a draft names it, a session in this workspace cannot search it.
    agent_id = await new_agent(owner)
    await attach(owner, agent_id, [foreign_id])
    draft = (await owner.get(f"/v1/agents/{agent_id}/draft")).json()
    issues = (await owner.post(f"/v1/agents/{agent_id}/validate", json=draft["spec"])).json()
    assert "missing_knowledge" in [i["code"] for i in issues["issues"]]


async def test_rejects_unsupported_empty_and_oversized_files(owner):  # MVP AC-14
    bad = await owner.post("/v1/knowledge", files={"file": ("photo.png", b"\x89PNG", "image/png")})
    assert bad.status_code == 422 and "Markdown, text or PDF" in bad.json()["detail"]
    empty = await owner.post("/v1/knowledge", files={"file": ("a.txt", b"", "text/plain")})
    assert empty.status_code == 422
    big = b"a" * (20 * 1024 * 1024 + 1)
    huge = await owner.post("/v1/knowledge", files={"file": ("a.txt", big, "text/plain")})
    assert huge.status_code == 413


async def test_unreadable_pdf_fails_with_a_reason(owner):
    source = await upload(owner, "scan.pdf", b"not really a pdf", "application/pdf")
    await index_all()
    failed = (await owner.get(f"/v1/knowledge/{source['id']}")).json()
    assert failed["status"] == "failed" and "not a valid PDF" in failed["error"]


async def test_embedding_failure_is_shown_and_retried(owner):
    class Broken(HashEmbedder):
        def passages(self, texts):
            raise RuntimeError("model download failed")

    set_embedder(Broken())
    source = await upload(owner, "handbook.md", HANDBOOK)
    await index_all()
    failed = (await owner.get(f"/v1/knowledge/{source['id']}")).json()
    assert failed["status"] == "failed" and "RuntimeError" in failed["error"]
    set_embedder(HashEmbedder())
    await owner.post(f"/v1/knowledge/{source['id']}/reindex")
    await index_all()
    assert (await owner.get(f"/v1/knowledge/{source['id']}")).json()["status"] == "ready"


async def test_delete_blocked_while_a_published_version_uses_it(owner):  # MVP DD-2
    source = await upload(owner, "handbook.md", HANDBOOK)
    await index_all()
    agent_id = await new_agent(owner)
    await attach(owner, agent_id, [source["id"]])
    assert (
        await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "v1"})
    ).status_code == 201
    blocked = await owner.delete(f"/v1/knowledge/{source['id']}")
    assert blocked.status_code == 409 and "Ava v1" in blocked.json()["detail"]

    unused = await upload(owner, "parking.md", OTHER)
    assert (await owner.delete(f"/v1/knowledge/{unused['id']}")).status_code == 204
    assert (await owner.get(f"/v1/knowledge/{unused['id']}")).status_code == 404


async def test_draft_using_a_deleted_source_is_flagged(owner):  # MVP AC-7
    source = await upload(owner, "parking.md", OTHER)
    agent_id = await new_agent(owner)
    await attach(owner, agent_id, [source["id"]])
    await owner.delete(f"/v1/knowledge/{source['id']}")
    draft = (await owner.get(f"/v1/agents/{agent_id}/draft")).json()
    issues = (await owner.post(f"/v1/agents/{agent_id}/validate", json=draft["spec"])).json()
    assert "missing_knowledge" in [i["code"] for i in issues["issues"]]


def test_chunks_keep_heading_path_and_overlap():
    text = (
        "# Guide\n## Prices\n" + " ".join(f"w{i}" for i in range(1000)) + "\n## Hours\nOpen daily."
    )
    chunks = chunk_text(text, max_words=600, overlap=75)
    assert len(chunks) == 3
    assert chunks[0].startswith("Guide > Prices\nw0 ") and chunks[0].endswith("w599")
    assert chunks[1].startswith("Guide > Prices\nw525 ")
    assert chunks[2] == "Guide > Hours\nOpen daily."


def test_plain_text_without_headings_is_one_chunk():
    assert chunk_text("Just a short note.") == ["Just a short note."]
