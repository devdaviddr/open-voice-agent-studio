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
RUN uv sync --frozen --no-dev --package ovas-runtime --no-install-workspace
COPY packages/core packages/core
COPY services/runtime services/runtime
RUN uv sync --frozen --no-dev --package ovas-runtime
EXPOSE 8100
CMD ["sh", "-c", "exec uv run --no-sync uvicorn ovas_runtime.main:app --host 0.0.0.0 --port 8100"]
