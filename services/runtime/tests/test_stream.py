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
