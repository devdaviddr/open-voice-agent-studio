"""Read-aloud: proxies the Kokoro provider for signed-in users (MVP FR-19)."""

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from ovas_api.auth import CurrentUser
from ovas_api.config import get_settings

router = APIRouter(prefix="/v1", tags=["tts"])


async def _forward(method: str, path: str, body: bytes | None = None) -> Response:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.request(
                method,
                f"{get_settings().tts_url}{path}",
                content=body,
                headers={"content-type": "application/json"} if body else None,
            )
    except httpx.HTTPError as e:
        raise HTTPException(502, "The text-to-speech service is not reachable.") from e
    return Response(res.content, res.status_code, media_type=res.headers.get("content-type"))


@router.get("/voices")
async def voices(_: CurrentUser) -> Response:
    return await _forward("GET", "/voices")


@router.post("/tts", response_class=Response, responses={200: {"content": {"audio/wav": {}}}})
async def tts(request: Request, _: CurrentUser) -> Response:
    return await _forward("POST", "/tts", await request.body())
