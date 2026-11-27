# Build context: repo root (uv workspace).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY services/api/pyproject.toml services/api/
COPY services/runtime/pyproject.toml services/runtime/
COPY providers/tts-kokoro/pyproject.toml providers/tts-kokoro/
COPY providers/stt-whisper/pyproject.toml providers/stt-whisper/
RUN uv sync --frozen --no-dev --package ovas-api --no-install-workspace
COPY packages/core packages/core
COPY services/api services/api
RUN uv sync --frozen --no-dev --package ovas-api
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync alembic -c services/api/alembic.ini upgrade head && exec uv run --no-sync uvicorn ovas_api.main:app --host 0.0.0.0 --port 8000"]
