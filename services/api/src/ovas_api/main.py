import httpx
from fastapi import FastAPI
from sqlalchemy import text

from ovas_api import __version__
from ovas_api.config import get_settings
from ovas_api.db import get_engine
from ovas_api.routes import agents, auth, settings, tts
from ovas_api.security import OriginGuard

app = FastAPI(title="Open Voice Agent Studio API", version=__version__)
app.add_middleware(OriginGuard)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(tts.router)
app.include_router(agents.router)


async def service_health(base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{base_url}/health")
            res.raise_for_status()
            return res.json()
    except httpx.HTTPError:
        return {"status": "unreachable"}


async def db_health() -> dict:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:  # any driver or network error means the database is not usable
        return {"status": "unreachable", "detail": type(e).__name__}


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "api": {"status": "ok", "version": __version__},
        "db": await db_health(),
        "runtime": await service_health(settings.runtime_url),
        "tts": await service_health(settings.tts_url),
    }
