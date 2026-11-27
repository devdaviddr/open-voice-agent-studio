import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from ovas_tts_kokoro import main
from ovas_tts_kokoro.engine import SAMPLE_RATE


class FakeEngine:
    def voices(self):
        return ["af_heart", "am_adam"]

    def synthesize(self, text, voice, speed, lang):
        return np.zeros(SAMPLE_RATE // 2, dtype=np.float32)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "models_present", lambda: True)
    main.app.dependency_overrides[main.engine] = FakeEngine
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_tts_returns_wav(client):
    res = client.post("/tts", json={"text": "Hello there."})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"
    data, sr = sf.read(io.BytesIO(res.content))
    assert sr == SAMPLE_RATE
    assert len(data) == SAMPLE_RATE // 2


def test_unknown_voice_is_rejected(client):
    res = client.post("/tts", json={"text": "Hi", "voice": "nope"})
    assert res.status_code == 422


def test_empty_text_is_rejected(client):
    assert client.post("/tts", json={"text": ""}).status_code == 422


def test_voices_lists_default(client):
    body = client.get("/voices").json()
    assert body["default"] == "af_heart"
    assert "af_heart" in body["voices"]


def test_missing_models_reported(monkeypatch):
    monkeypatch.setattr(main, "models_present", lambda: False)
    c = TestClient(main.app)
    assert c.get("/health").json()["status"] == "models missing"
    assert c.post("/tts", json={"text": "Hi"}).status_code == 503
