import os

import httpx
from fastapi import FastAPI

from agent import __version__

AUDIO_URL = os.environ.get("AUDIO_URL", "http://localhost:8001")

app = FastAPI(title="Open Voice Agent Studio: agent", version=__version__)


async def audio_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{AUDIO_URL}/health")
            res.raise_for_status()
            return res.json()
    except httpx.HTTPError:
        return {"status": "unreachable"}


@app.get("/health")
async def health() -> dict:
    return {
        "agent": {"status": "ok", "version": __version__},
        "audio": await audio_health(),
    }
