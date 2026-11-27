"""Local text embeddings (fastembed, BAAI/bge-small-en-v1.5, 384-d)."""

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from ovas_api.config import get_settings
from ovas_api.models import EMBEDDING_DIM


class Embedder(Protocol):
    def passages(self, texts: list[str]) -> list[list[float]]: ...
    def query(self, text: str) -> list[float]: ...


class FastEmbedder:
    """Downloads the model on first use into OVAS_EMBEDDING_CACHE_DIR."""

    def __init__(self, model: str, cache_dir: str | None) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model, cache_dir=cache_dir)

    def passages(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.passage_embed(texts)]

    def query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


class HashEmbedder:
    """Deterministic bag-of-words vectors for tests: texts sharing words score higher."""

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
            v[h % EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def query(self, text: str) -> list[float]:
        return self._vec(text)


_override: Embedder | None = None


def set_embedder(embedder: Embedder | None) -> None:
    """Replace the embedder (tests); None restores the default."""
    global _override
    _override = embedder


@lru_cache(maxsize=1)
def _default() -> Embedder:
    s = get_settings()
    return FastEmbedder(s.embedding_model, s.embedding_cache_dir)


def get_embedder() -> Embedder:
    return _override or _default()
