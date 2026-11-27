# Open Voice Agent Studio

An open-source studio for building, running and testing voice agents.

> Early days: this is a runnable skeleton. The voice pipeline is not built yet.

## Architecture

| Service    | Stack                                  | Port | Role                                          |
|------------|----------------------------------------|------|-----------------------------------------------|
| `frontend` | React, TypeScript, Vite, Tailwind, shadcn/ui | 5173 | Studio UI                              |
| `agent`    | Python 3.12, FastAPI, uv               | 8000 | Agent orchestration (speech-to-text, LLM, text-to-speech) |
| `audio`    | Rust, Axum, Tokio                      | 8001 | Low-latency audio streaming                   |

The frontend proxies `/api/*` to the agent. The agent calls the audio service.

## Quick start

```sh
docker compose up --build
```

Open http://localhost:5173. The Services card should show both `agent` and `audio` as `ok`.

## Local development

```sh
# frontend
cd frontend && pnpm install && pnpm dev

# agent
cd agent && uv sync && uv run uvicorn agent.main:app --reload --port 8000

# audio (needs a Rust toolchain)
cd audio && cargo run
```

## Checks

```sh
cd frontend && pnpm build && pnpm lint
cd agent && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd audio && cargo build
```

## License

MIT
