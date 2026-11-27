from fastapi.testclient import TestClient

from agent.main import app


def test_health_reports_unreachable_audio(monkeypatch):
    monkeypatch.setattr("agent.main.AUDIO_URL", "http://127.0.0.1:9")
    body = TestClient(app).get("/health").json()
    assert body["agent"]["status"] == "ok"
    assert body["audio"]["status"] == "unreachable"
