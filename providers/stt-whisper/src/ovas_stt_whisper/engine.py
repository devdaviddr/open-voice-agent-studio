"""Whisper speech-to-text engine (faster-whisper, CTranslate2)."""

import io
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MODELS_DIR = Path(os.environ.get("MODELS_DIR", Path(__file__).resolve().parents[2] / "models"))
MODEL = os.environ.get("OVAS_WHISPER_MODEL", "base")
COMPUTE_TYPE = os.environ.get("OVAS_WHISPER_COMPUTE_TYPE", "int8")


@dataclass
class Transcript:
    text: str
    language: str
    duration_ms: int


class Engine:
    def __init__(self, model: str = MODEL, models_dir: Path = MODELS_DIR):
        from faster_whisper import WhisperModel

        self.model_name = model
        self._model = WhisperModel(
            model, device="cpu", compute_type=COMPUTE_TYPE, download_root=str(models_dir)
        )

    def transcribe(self, audio: bytes, language: str | None) -> Transcript:
        segments, info = self._model.transcribe(
            io.BytesIO(audio), language=language, beam_size=1, vad_filter=True
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return Transcript(text=text, language=info.language, duration_ms=int(info.duration * 1000))


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return Engine()
