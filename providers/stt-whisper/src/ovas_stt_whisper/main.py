import asyncio
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from ovas_stt_whisper import __version__
from ovas_stt_whisper.engine import MODEL, Engine, get_engine

log = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Open Voice Agent Studio: stt", version=__version__)


class TranscriptOut(BaseModel):
    text: str
    language: str
    duration_ms: int


def engine() -> Engine:
    try:
        return get_engine()
    except Exception as e:  # model download or load failed
        log.exception("Whisper model could not be loaded")
        raise HTTPException(503, f"Whisper model '{MODEL}' could not be loaded: {e}") from e


EngineDep = Annotated[Engine, Depends(engine)]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "model": f"whisper-{MODEL}"}


@app.post("/stt")
async def stt(
    request: Request,
    eng: EngineDep,
    language: Annotated[str | None, Query(max_length=10)] = None,
) -> TranscriptOut:
    audio = await request.body()
    if not audio:
        raise HTTPException(422, "Send the recorded audio as the request body.")
    if len(audio) > MAX_BYTES:
        raise HTTPException(413, "The recording is too long; keep clips under a minute.")
    try:
        t = await asyncio.to_thread(eng.transcribe, audio, language or None)
    except (ValueError, OSError) as e:  # PyAV raises these subclasses for undecodable audio
        raise HTTPException(422, "The audio could not be decoded; record again.") from e
    return TranscriptOut(text=t.text, language=t.language, duration_ms=t.duration_ms)
