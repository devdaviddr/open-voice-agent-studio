"""Kokoro-82M (ONNX) text-to-speech engine."""

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

MODELS_DIR = Path(os.environ.get("MODELS_DIR", Path(__file__).resolve().parents[2] / "models"))
MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"
SAMPLE_RATE = 24_000


class Engine:
    def __init__(self, models_dir: Path = MODELS_DIR):
        from kokoro_onnx import Kokoro

        self._kokoro = Kokoro(str(models_dir / MODEL_FILE), str(models_dir / VOICES_FILE))

    def voices(self) -> list[str]:
        return sorted(self._kokoro.get_voices())

    def synthesize(self, text: str, voice: str, speed: float, lang: str) -> np.ndarray:
        samples, _ = self._kokoro.create(text, voice=voice, speed=speed, lang=lang)
        return samples


def models_present(models_dir: Path = MODELS_DIR) -> bool:
    return (models_dir / MODEL_FILE).is_file() and (models_dir / VOICES_FILE).is_file()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return Engine()
