import os

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

from agent import __version__

AUDIO_URL = os.environ.get("AUDIO_URL", "http://localhost:8001")
TTS_URL = os.environ.get("TTS_URL", "http://localhost:8002")

app = FastAPI(title="Open Voice Agent Studio: agent", version=__version__)


async def service_health(base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{base_url}/health")
            res.raise_for_status()
            return res.json()
    except httpx.HTTPError:
        return {"status": "unreachable"}


async def forward_to_tts(method: str, path: str, body: bytes | None = None) -> Response:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.request(
                method,
                f"{TTS_URL}{path}",
                content=body,
                headers={"content-type": "application/json"} if body else None,
            )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"tts service unreachable: {e}") from e
    return Response(res.content, res.status_code, media_type=res.headers.get("content-type"))


@app.get("/health")
async def health() -> dict:
    return {
        "agent": {"status": "ok", "version": __version__},
        "audio": await service_health(AUDIO_URL),
        "tts": await service_health(TTS_URL),
    }


@app.get("/voices")
async def voices() -> Response:
    return await forward_to_tts("GET", "/voices")


@app.post("/tts")
async def tts(request: Request) -> Response:
    return await forward_to_tts("POST", "/tts", await request.body())
