"""Push-to-talk: proxies the Whisper provider for signed-in users (MVP FR-23)."""

from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ovas_api.auth import CurrentUser
from ovas_api.config import get_settings

router = APIRouter(prefix="/v1", tags=["stt"])

MAX_BYTES = 10 * 1024 * 1024


class Transcript(BaseModel):
    text: str
    language: str
    duration_ms: int


@router.post(
    "/stt",
    openapi_extra={
        "requestBody": {"required": True, "content": {"audio/*": {"schema": {"type": "string"}}}}
    },
)
async def stt(
    request: Request,
    _: CurrentUser,
    language: Annotated[str | None, Query(max_length=10)] = None,
) -> Transcript:
    audio = await request.body()
    if not audio:
        raise HTTPException(422, "Send the recorded audio as the request body.")
    if len(audio) > MAX_BYTES:
        raise HTTPException(413, "The recording is too long; keep clips under a minute.")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                f"{get_settings().stt_url}/stt",
                content=audio,
                params={"language": language} if language else None,
                headers={
                    "content-type": request.headers.get("content-type", "application/octet-stream")
                },
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            502, "The speech-to-text service is not reachable. Is stt-whisper running?"
        ) from e
    if res.status_code != 200:
        detail = res.json().get("detail") if "json" in res.headers.get("content-type", "") else None
        raise HTTPException(res.status_code, detail or "Speech-to-text failed; record again.")
    return Transcript.model_validate(res.json())
