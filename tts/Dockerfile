FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --no-dev
ENV MODELS_DIR=/models
EXPOSE 8002
CMD ["sh", "-c", "scripts/fetch-models.sh && exec uv run --no-sync uvicorn tts.main:app --host 0.0.0.0 --port 8002"]
