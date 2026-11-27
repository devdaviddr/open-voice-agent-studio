import pytest
from fastapi.testclient import TestClient

from ovas_stt_whisper import main
from ovas_stt_whisper.engine import Transcript


class FakeEngine:
    def __init__(self):
        self.calls: list[tuple[bytes, str | None]] = []

    def transcribe(self, audio: bytes, language: str | None) -> Transcript:
        self.calls.append((audio, language))
        if audio == b"garbage":
            raise ValueError("invalid data")
        return Transcript(text="hello there", language=language or "en", duration_ms=1200)


@pytest.fixture
def fake():
    return FakeEngine()


@pytest.fixture
def client(fake):
    main.app.dependency_overrides[main.engine] = lambda: fake
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_transcribes_audio(client, fake):  # MVP AC-21
    res = client.post(
        "/stt?language=en", content=b"RIFF....", headers={"content-type": "audio/wav"}
    )
    assert res.status_code == 200
    assert res.json() == {"text": "hello there", "language": "en", "duration_ms": 1200}
    assert fake.calls == [(b"RIFF....", "en")]


def test_language_is_optional(client, fake):
    assert client.post("/stt", content=b"x").status_code == 200
    assert fake.calls[0][1] is None


def test_empty_body_rejected(client):
    assert client.post("/stt", content=b"").status_code == 422


def test_oversized_clip_rejected(client):
    assert client.post("/stt", content=b"0" * (main.MAX_BYTES + 1)).status_code == 413


def test_undecodable_audio_rejected(client):
    res = client.post("/stt", content=b"garbage")
    assert res.status_code == 422 and "decoded" in res.json()["detail"]


def test_health_names_model():
    body = TestClient(main.app).get("/health").json()
    assert body["status"] == "ok" and body["model"].startswith("whisper-")
