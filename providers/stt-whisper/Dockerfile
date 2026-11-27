# Build context: repo root (uv workspace).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy MODELS_DIR=/models
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY services/api/pyproject.toml services/api/
COPY services/runtime/pyproject.toml services/runtime/
COPY providers/tts-kokoro/pyproject.toml providers/tts-kokoro/
COPY providers/stt-whisper/pyproject.toml providers/stt-whisper/
RUN uv sync --frozen --no-dev --package ovas-stt-whisper --no-install-workspace
COPY providers/stt-whisper providers/stt-whisper
RUN uv sync --frozen --no-dev --package ovas-stt-whisper
EXPOSE 8003
CMD ["uv", "run", "--no-sync", "uvicorn", "ovas_stt_whisper.main:app", "--host", "0.0.0.0", "--port", "8003"]
