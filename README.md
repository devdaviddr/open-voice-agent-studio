# Open Voice Agent Studio

An open-source, self-hosted studio for building voice agents. Design an agent as a conversation
workflow on a visual canvas, give it knowledge and memory, test it by talking to it, and publish
immutable versions. Runs fully on local models by default (Kokoro, Whisper, any OpenAI-compatible
LLM such as Ollama). MIT licensed.

> **Status: 0.3.0, the MVP.** Build agents on the canvas, give them documents and memory, test
> them by typing or push-to-talk, and publish versions. Real-time voice for callers, tools and the
> embeddable widget are next; see the [milestones](spec/product).

## What you can do

- **Design** an agent as a workflow of steps, routers and data-collecting nodes, with typed
  variables and conditions in plain language or expressions. Problems show on the canvas.
- **Ground** it in your documents (Markdown, text, PDF), searched locally.
- **Remember** returning callers: lasting facts are saved after each conversation.
- **Test** it in a console beside the canvas, typed or spoken, with replies read aloud and the
  canvas showing what the agent is doing.
- **Publish** immutable versions, compare them, and roll back.
- **Keep everything local**: your LLM, Kokoro, Whisper and the embedding model all run on your
  machine by default.

## Architecture

| Path | Role | Stack | Port |
| --- | --- | --- | --- |
| `apps/web` | Studio UI | React, TypeScript, Vite, React Flow, shadcn/ui | 5173 |
| `services/api` | Control plane: accounts, agents, versions, knowledge, sessions | Python, FastAPI, SQLAlchemy, Alembic | 8000 |
| `services/runtime` | Runs agent sessions | Python, FastAPI | 8100 |
| `packages/core` | Shared AgentSpec schema, validation, workflow engine | Python, Pydantic | — |
| `providers/tts-kokoro` | Text-to-speech, [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Python, kokoro-onnx | 8002 |
| `providers/stt-whisper` | Speech-to-text for push-to-talk, [Whisper](https://github.com/SYSTRAN/faster-whisper) | Python, faster-whisper | 8003 |
| `db` | Postgres 17 with pgvector | — | internal |

The agent workflow schema is defined once in `packages/core` and generated into TypeScript for the
studio (`make gen`). Design decisions are recorded in [`docs/adr`](docs/adr).

## Quick start

Requirements: Docker, plus `uv` and `pnpm` for local development.

```sh
make up        # builds and starts everything
```

Open http://localhost:5173, sign up (the first account owns the workspace), and point **Settings →
LLM** at your model; Ollama on the same machine with `qwen3.5:9b` works out of the box. Models for
speech and search download on first use. The [getting started guide](docs/getting-started.md)
walks through your first agent.

## Documentation

- [Getting started](docs/getting-started.md)
- [Concepts](docs/concepts.md): agents, nodes, edges, variables, versions, knowledge, memory
- [Architecture](docs/architecture.md) and the [decision records](docs/adr)
- [Changelog](CHANGELOG.md)

## Development

```sh
make install   # Python (uv) and JS (pnpm) dependencies, git hooks
make dev       # backend in Docker, studio with hot reload
make check     # lint, typecheck, codegen drift, tests (80% API coverage floor): what CI runs
make e2e       # Playwright end to end against a throwaway stack with a stub LLM
make help      # every target
```

The project is built spec-first: read [`spec/README.md`](spec/README.md) before starting a change.
AI coding agents: start with [`CLAUDE.md`](CLAUDE.md).

## License

MIT. Kokoro-82M model weights are Apache 2.0; Whisper weights are MIT; bge-small-en-v1.5 is MIT.
