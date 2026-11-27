from fastapi.testclient import TestClient

from agent.main import app


def test_health_reports_unreachable_services(monkeypatch):
    monkeypatch.setattr("agent.main.AUDIO_URL", "http://127.0.0.1:9")
    monkeypatch.setattr("agent.main.TTS_URL", "http://127.0.0.1:9")
    body = TestClient(app).get("/health").json()
    assert body["agent"]["status"] == "ok"
    assert body["audio"]["status"] == "unreachable"
    assert body["tts"]["status"] == "unreachable"


def test_tts_returns_502_when_service_down(monkeypatch):
    monkeypatch.setattr("agent.main.TTS_URL", "http://127.0.0.1:9")
    res = TestClient(app).post("/tts", json={"text": "hi"})
    assert res.status_code == 502
