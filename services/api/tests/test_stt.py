import httpx

from ovas_api.config import get_settings
from ovas_api.routes import stt

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt "
AUDIO = {"content-type": "audio/wav"}


class FakeProvider:
    """Stands in for providers/stt-whisper via httpx's mock transport."""

    def __init__(self, response: httpx.Response | None = None):
        self.requests: list[httpx.Request] = []
        self.response = response or httpx.Response(
            200, json={"text": "hello", "language": "en", "duration_ms": 900}
        )

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.response


def patch_provider(monkeypatch, provider) -> None:
    real = httpx.AsyncClient

    def client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(provider)
        return real(*args, **kwargs)

    monkeypatch.setattr(stt.httpx, "AsyncClient", client)


async def test_transcribes_for_signed_in_user(owner, monkeypatch):  # MVP AC-21
    provider = FakeProvider()
    patch_provider(monkeypatch, provider)
    res = await owner.post(
        "/v1/stt?language=en", content=WAV, headers={"content-type": "audio/webm"}
    )
    assert res.status_code == 200
    assert res.json() == {"text": "hello", "language": "en", "duration_ms": 900}
    sent = provider.requests[0]
    assert str(sent.url) == f"{get_settings().stt_url}/stt?language=en"
    assert sent.headers["content-type"] == "audio/webm"
    assert sent.content == WAV


async def test_requires_sign_in(client):  # MVP AC-21
    assert (await client.post("/v1/stt", content=WAV)).status_code == 401


async def test_provider_down_is_502(owner, monkeypatch):  # MVP AC-21
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    patch_provider(monkeypatch, down)
    res = await owner.post("/v1/stt", content=WAV, headers=AUDIO)
    assert res.status_code == 502
    assert "not reachable" in res.json()["detail"]


async def test_provider_error_is_passed_on(owner, monkeypatch):
    bad = httpx.Response(422, json={"detail": "The audio could not be decoded; record again."})
    patch_provider(monkeypatch, FakeProvider(bad))
    res = await owner.post("/v1/stt", content=b"garbage", headers=AUDIO)
    assert res.status_code == 422 and "decoded" in res.json()["detail"]


async def test_empty_and_oversized_rejected(owner):
    assert (await owner.post("/v1/stt", content=b"")).status_code == 422
    big = b"0" * (stt.MAX_BYTES + 1)
    assert (await owner.post("/v1/stt", content=big, headers=AUDIO)).status_code == 413


async def test_non_audio_body_still_blocked_by_origin_guard(owner):  # MVP AC-3
    res = await owner.post("/v1/stt", content=WAV, headers={"content-type": "text/plain"})
    assert res.status_code == 415
