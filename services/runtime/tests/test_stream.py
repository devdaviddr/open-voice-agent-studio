from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ovas_core.templates import receptionist
from ovas_core.testing import FakeLlm
from ovas_core.tokens import sign_session
from ovas_runtime import main
from ovas_runtime.config import get_settings


class FakeApi:
    stored: list[dict[str, Any]] = []
    ended: dict[str, Any] | None = None

    async def session(self, session_id: str) -> dict[str, Any]:
        return {
            "spec": receptionist().model_dump(mode="json"),
            "variables": {},
            "ended": False,
            "llm": {"base_url": "x", "model": "m", "api_key": None, "reasoning_effort": None},
        }

    async def events(self, session_id: str, events: list[dict[str, Any]]) -> None:
        FakeApi.stored += events

    async def end(self, session_id: str, body: dict[str, Any]) -> None:
        FakeApi.ended = body

    async def aclose(self) -> None:
        pass


@pytest.fixture
def client(monkeypatch):
    FakeApi.stored, FakeApi.ended = [], None
    monkeypatch.setattr(main, "ApiClient", FakeApi)
    llm = FakeLlm(replies=["Happy to help with prices."], choices=[2])
    monkeypatch.setattr(main, "make_llm", lambda _: llm)
    return TestClient(main.app)


def test_turn_streams_tokens_and_events(client):  # MVP AC-16
    token = sign_session("s1", get_settings().internal_key)
    with client.websocket_connect(f"/v1/sessions/s1/stream?token={token}") as ws:
        first = []
        while not first or first[-1]["type"] != "assistant_message":
            first.append(ws.receive_json())
        assert first[-1]["text"].startswith("Hi, Bright Smile Dental")
        ws.send_json({"type": "user_message", "text": "How much is a cleaning?"})
        events = []
        while not events or events[-1]["type"] != "assistant_message":
            events.append(ws.receive_json())
        kinds = [e["type"] for e in events]
        assert kinds.index("user_message") < kinds.index("token")
        assert "edge" in kinds and "node_enter" in kinds and "token" in kinds
        assert events[-1]["text"] == "Happy to help with prices."
        ws.send_json({"type": "end"})
    stored = [e["type"] for e in FakeApi.stored]
    assert "token" not in stored and "assistant_message" in stored and "edge" in stored
    assert FakeApi.ended and FakeApi.ended["outcome"] == "ended_by_user"


def test_bad_token_rejected(client):
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/v1/sessions/s1/stream?token=nope") as ws,
    ):
        ws.receive_json()


class KnowledgeApi(FakeApi):
    searches: list[tuple[str, list[str] | None, int]] = []

    async def session(self, session_id: str) -> dict[str, Any]:
        data = await super().session(session_id)
        data["spec"]["knowledge"] = [{"source_id": "src-1"}]
        return data

    async def search_knowledge(self, session_id, query, source_ids, k):
        KnowledgeApi.searches.append((query, source_ids, k))
        return [{"source": "handbook.md", "text": "A cleaning costs 145 dollars.", "score": 0.9}]


def test_attached_knowledge_is_searched(monkeypatch):  # MVP AC-14
    KnowledgeApi.searches = []
    monkeypatch.setattr(main, "ApiClient", KnowledgeApi)
    llm = FakeLlm(replies=["A cleaning costs 145 dollars."], choices=[2])
    monkeypatch.setattr(main, "make_llm", lambda _: llm)
    token = sign_session("s1", get_settings().internal_key)
    with TestClient(main.app).websocket_connect(f"/v1/sessions/s1/stream?token={token}") as ws:
        while ws.receive_json()["type"] != "assistant_message":
            pass
        ws.send_json({"type": "user_message", "text": "How much is a cleaning?"})
        events = []
        while not events or events[-1]["type"] != "assistant_message":
            events.append(ws.receive_json())
        ws.send_json({"type": "end"})
    assert KnowledgeApi.searches and KnowledgeApi.searches[0][0] == "How much is a cleaning?"
    knowledge = next(e for e in events if e["type"] == "knowledge")
    assert knowledge["results"][0]["source"] == "handbook.md"
    system = llm.stream_calls[-1]["messages"][0]["content"]
    assert "145 dollars" in system  # auto top-k injected into the prompt


def test_agent_without_knowledge_never_searches(client, monkeypatch):
    called = []
    monkeypatch.setattr(FakeApi, "search_knowledge", lambda *a: called.append(a), raising=False)
    token = sign_session("s1", get_settings().internal_key)
    with client.websocket_connect(f"/v1/sessions/s1/stream?token={token}") as ws:
        while ws.receive_json()["type"] != "assistant_message":
            pass
        ws.send_json({"type": "user_message", "text": "How much is a cleaning?"})
        while ws.receive_json()["type"] != "assistant_message":
            pass
        ws.send_json({"type": "end"})
    assert called == []
