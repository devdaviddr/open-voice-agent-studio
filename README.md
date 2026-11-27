# Open Voice Agent Studio

An open-source, self-hosted studio for building voice agents. Design an agent as a conversation
workflow on a visual canvas, give it knowledge and memory, test it by talking to it, and publish
immutable versions. Runs fully on local models by default (Kokoro, Whisper, any OpenAI-compatible
LLM such as Ollama). MIT licensed.

> **Status: building the MVP.** The foundations are in place (monorepo, database, schema, checks).
> Sign-in, the builder, versions, context and the test console are in progress; see
> [`spec/mvp`](spec/mvp) and the [milestones](spec/product).

## Architecture

| Path | Role | Stack | Port |
| --- | --- | --- | --- |
| `apps/web` | Studio UI | React, TypeScript, Vite, React Flow, shadcn/ui | 5173 |
| `services/api` | Control plane: accounts, agents, versions, knowledge, sessions | Python, FastAPI, SQLAlchemy, Alembic | 8000 |
| `services/runtime` | Runs agent sessions | Python, FastAPI | 8100 |
| `packages/core` | Shared AgentSpec schema, validation, workflow engine | Python, Pydantic | — |
| `providers/tts-kokoro` | Text-to-speech, [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Python, kokoro-onnx | 8002 |
| `db` | Postgres 17 with pgvector | — | internal |

The agent workflow schema is defined once in `packages/core` and generated into TypeScript for the
studio (`make gen`). Design decisions are recorded in [`docs/adr`](docs/adr).

## Quick start

Requirements: Docker, plus `uv` and `pnpm` for local development.

```sh
make up        # builds and starts everything
```

Open http://localhost:5173. The first start downloads the Kokoro model (about 350 MB) into a Docker
volume.

## Development

```sh
make install   # Python (uv) and JS (pnpm) dependencies, git hooks
make dev       # backend in Docker, studio with hot reload
make check     # lint, typecheck, codegen drift, tests: what CI runs
make help      # every target
```

The project is built spec-first: read [`spec/README.md`](spec/README.md) before starting a change.
AI coding agents: start with [`CLAUDE.md`](CLAUDE.md).

## License

MIT. Kokoro-82M model weights are Apache 2.0.
