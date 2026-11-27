import json

import httpx
import pytest
from sqlalchemy import select

from ovas_api import jobs
from ovas_api.db import get_sessionmaker
from ovas_api.knowledge.embedding import HashEmbedder, set_embedder
from ovas_api.memory import extract
from ovas_api.models import Job

from .test_sessions import internal_headers, new_agent


class FakeLlm:
    """An OpenAI-compatible /chat/completions endpoint (tests never call a real model)."""

    def __init__(self, *facts: list[str], reject_schema: bool = False, down: bool = False):
        self.replies = list(facts)
        self.reject_schema, self.down = reject_schema, down
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("refused", request=request)
        body = json.loads(request.content)
        self.requests.append(body)
        if self.reject_schema and body["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": "json_schema not supported"})
        facts = self.replies.pop(0) if self.replies else []
        content = json.dumps({"facts": facts})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    set_embedder(HashEmbedder())
    yield
    set_embedder(None)
    monkeypatch.setattr(extract, "transport", None)


def use_llm(monkeypatch, llm: FakeLlm) -> FakeLlm:
    monkeypatch.setattr(extract, "transport", httpx.MockTransport(llm))
    return llm


async def memory_agent(c, enabled: bool = True) -> str:
    agent_id = await new_agent(c)
    draft = (await c.get(f"/v1/agents/{agent_id}/draft")).json()
    draft["spec"]["memory"] = {"enabled": enabled}
    assert (await c.put(f"/v1/agents/{agent_id}/draft", json=draft)).status_code == 200
    return agent_id


async def talk(c, agent_id: str, end_user: str | None, said: str) -> str:
    body = {"agent_id": agent_id, "end_user_id": end_user}
    sid = (await c.post("/v1/sessions", json=body)).json()["session_id"]
    events = [
        {"type": "assistant_message", "payload": {"text": "Hi, how can I help?"}},
        {"type": "user_message", "payload": {"text": said}},
        {"type": "assistant_message", "payload": {"text": "Got it."}},
    ]
    await c.post(f"/internal/sessions/{sid}/events", json=events, headers=internal_headers())
    await c.post(
        f"/internal/sessions/{sid}/end",
        json={"outcome": None, "variables": {}, "usage": {}},
        headers=internal_headers(),
    )
    await jobs.run_pending(get_sessionmaker())
    return sid


async def recall(c, agent_id: str, end_user: str | None, query: str = "") -> list[str]:
    body = {"agent_id": agent_id, "end_user_id": end_user}
    sid = (await c.post("/v1/sessions", json=body)).json()["session_id"]
    res = await c.post(
        f"/internal/sessions/{sid}/memory/recall", json={"query": query}, headers=internal_headers()
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_remembers_and_forgets_a_caller(owner, monkeypatch):  # MVP AC-15
    llm = use_llm(monkeypatch, FakeLlm(["Their dog is called Rex."]))
    agent_id = await memory_agent(owner)
    first = await talk(owner, agent_id, "ana", "My dog Rex needs a vet check next week.")
    assert "Caller: My dog Rex" in llm.requests[0]["messages"][0]["content"]

    assert await recall(owner, agent_id, "ana") == ["Their dog is called Rex."]
    assert await recall(owner, agent_id, "ana", "what pet does she have dog") == [
        "Their dog is called Rex."
    ]
    assert await recall(owner, agent_id, "bob") == []  # another caller

    events = (await owner.get(f"/v1/sessions/{first}")).json()["events"]
    assert events[-1]["type"] == "memory_saved"
    assert events[-1]["payload"] == {"facts": ["Their dog is called Rex."]}

    listed = (await owner.get(f"/v1/agents/{agent_id}/memories")).json()
    assert [(m["end_user_id"], m["fact"]) for m in listed] == [("ana", "Their dog is called Rex.")]
    assert listed[0]["session_id"] == first
    deleted = await owner.delete(f"/v1/agents/{agent_id}/memories/{listed[0]['id']}")
    assert deleted.status_code == 204
    assert await recall(owner, agent_id, "ana") == []


async def test_known_facts_are_not_saved_twice(owner, monkeypatch):
    llm = use_llm(
        monkeypatch,
        FakeLlm(
            ["Their dog is called Rex."], ["Their dog is called Rex.", "They prefer mornings."]
        ),
    )
    agent_id = await memory_agent(owner)
    await talk(owner, agent_id, "ana", "My dog is Rex.")
    await talk(owner, agent_id, "ana", "Mornings suit me best.")
    assert "Their dog is called Rex." in llm.requests[1]["messages"][0]["content"]  # known
    facts = [m["fact"] for m in (await owner.get(f"/v1/agents/{agent_id}/memories")).json()]
    assert facts == ["Their dog is called Rex.", "They prefer mornings."]


async def test_no_memory_when_off_or_caller_unknown(owner, monkeypatch):
    llm = use_llm(monkeypatch, FakeLlm(["Should not be stored."]))
    off = await memory_agent(owner, enabled=False)
    await talk(owner, off, "ana", "My dog is Rex.")
    on = await memory_agent(owner)
    await talk(owner, on, None, "My dog is Rex.")
    assert llm.requests == []
    assert (await owner.get(f"/v1/agents/{on}/memories")).json() == []
    assert await recall(owner, off, "ana") == []


async def test_falls_back_to_plain_json_mode(owner, monkeypatch):
    llm = use_llm(monkeypatch, FakeLlm(["They live in Footscray."], reject_schema=True))
    agent_id = await memory_agent(owner)
    await talk(owner, agent_id, "ana", "I live in Footscray.")
    assert [r["response_format"]["type"] for r in llm.requests] == ["json_schema", "json_object"]
    assert await recall(owner, agent_id, "ana") == ["They live in Footscray."]


async def test_llm_failure_is_retried(owner, monkeypatch):
    use_llm(monkeypatch, FakeLlm(down=True))
    agent_id = await memory_agent(owner)
    await talk(owner, agent_id, "ana", "My dog is Rex.")
    async with get_sessionmaker()() as db:
        job = await db.scalar(select(Job).where(Job.kind == "extract_memory"))
    assert job is not None and job.status == "failed" and job.attempts == jobs.MAX_ATTEMPTS
    assert "ConnectError" in (job.error or "")


async def test_forget_a_caller_and_agent_scoping(owner, monkeypatch):
    use_llm(monkeypatch, FakeLlm(["Their dog is called Rex."], ["They like jazz."]))
    agent_id = await memory_agent(owner)
    await talk(owner, agent_id, "ana", "My dog is Rex.")
    await talk(owner, agent_id, "bob", "I like jazz.")
    other = await memory_agent(owner)
    assert (await owner.get(f"/v1/agents/{other}/memories")).json() == []
    ana = (await owner.get(f"/v1/agents/{agent_id}/memories", params={"end_user_id": "ana"})).json()
    wrong = await owner.delete(f"/v1/agents/{other}/memories/{ana[0]['id']}")
    assert wrong.status_code == 404
    res = await owner.delete(f"/v1/agents/{agent_id}/memories", params={"end_user_id": "ana"})
    assert res.status_code == 204
    left = (await owner.get(f"/v1/agents/{agent_id}/memories")).json()
    assert [m["end_user_id"] for m in left] == ["bob"]
