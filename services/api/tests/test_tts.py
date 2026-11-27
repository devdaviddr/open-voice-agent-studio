import httpx

from ovas_api.routes import tts

REAL_CLIENT = httpx.AsyncClient


def patch_provider(monkeypatch, handler) -> list[httpx.Request]:
    seen: list[httpx.Request] = []
    real = REAL_CLIENT

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    monkeypatch.setattr(
        tts.httpx,
        "AsyncClient",
        lambda *a, **kw: real(*a, **{**kw, "transport": httpx.MockTransport(record)}),
    )
    return seen


async def test_read_aloud_proxies_the_voice(owner, monkeypatch):  # MVP AC-17
    seen = patch_provider(
        monkeypatch,
        lambda r: httpx.Response(200, content=b"RIFF", headers={"content-type": "audio/wav"}),
    )
    res = await owner.post("/v1/tts", json={"text": "Hello", "voice": "am_adam", "speed": 1.1})
    assert res.status_code == 200 and res.headers["content-type"] == "audio/wav"
    assert seen[0].url.path == "/tts"
    assert seen[0].read() == b'{"text":"Hello","voice":"am_adam","speed":1.1}'


async def test_voices_and_provider_down(owner, monkeypatch):
    patch_provider(
        monkeypatch,
        lambda r: httpx.Response(200, json={"default": "af_heart", "voices": ["af_heart"]}),
    )
    assert (await owner.get("/v1/voices")).json()["default"] == "af_heart"

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    patch_provider(monkeypatch, down)
    res = await owner.post("/v1/tts", json={"text": "Hello"})
    assert res.status_code == 502 and "not reachable" in res.json()["detail"]


async def test_requires_sign_in(client):
    assert (await client.get("/v1/voices")).status_code == 401
