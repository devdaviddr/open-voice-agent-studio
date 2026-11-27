# Build context: repo root (uv workspace).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy MODELS_DIR=/models
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY services/api/pyproject.toml services/api/
COPY services/runtime/pyproject.toml services/runtime/
COPY providers/tts-kokoro/pyproject.toml providers/tts-kokoro/
COPY providers/stt-whisper/pyproject.toml providers/stt-whisper/
RUN uv sync --frozen --no-dev --package ovas-tts-kokoro --no-install-workspace
COPY providers/tts-kokoro providers/tts-kokoro
RUN uv sync --frozen --no-dev --package ovas-tts-kokoro
EXPOSE 8002
CMD ["sh", "-c", "providers/tts-kokoro/scripts/fetch-models.sh && exec uv run --no-sync uvicorn ovas_tts_kokoro.main:app --host 0.0.0.0 --port 8002"]
