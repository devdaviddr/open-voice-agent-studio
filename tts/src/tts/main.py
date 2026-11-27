import io
from typing import Annotated

import soundfile as sf
from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from tts import __version__
from tts.engine import SAMPLE_RATE, Engine, get_engine, models_present

DEFAULT_VOICE = "af_heart"

app = FastAPI(title="Open Voice Agent Studio: tts", version=__version__)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = DEFAULT_VOICE
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    lang: str = "en-us"


def engine() -> Engine:
    if not models_present():
        raise HTTPException(503, "Kokoro model files are missing; run scripts/fetch-models.sh")
    return get_engine()


EngineDep = Annotated[Engine, Depends(engine)]


@app.get("/health")
def health() -> dict:
    status = "ok" if models_present() else "models missing"
    return {"status": status, "version": __version__, "model": "kokoro-82m-v1.0-onnx"}


@app.get("/voices")
def voices(eng: EngineDep) -> dict:
    return {"default": DEFAULT_VOICE, "voices": eng.voices()}


@app.post("/tts", response_class=Response, responses={200: {"content": {"audio/wav": {}}}})
def tts(req: SpeakRequest, eng: EngineDep) -> Response:
    if req.voice not in eng.voices():
        raise HTTPException(422, f"Unknown voice: {req.voice}")
    samples = eng.synthesize(req.text, req.voice, req.speed, req.lang)
    buf = io.BytesIO()
    sf.write(buf, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return Response(buf.getvalue(), media_type="audio/wav")
