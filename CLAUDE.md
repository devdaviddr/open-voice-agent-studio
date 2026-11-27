# Open Voice Agent Studio

Open-source, self-hosted studio for building voice agents as conversation workflows on a React Flow
canvas. Code name and prefix: `ovas`. MIT.

## Rules that override everything else

1. **Spec first.** Code implements an approved spec in `spec/<feature>/<version>/` (spec → plan →
   tasks). If a change is not covered, update the spec and bump its version before coding
   (`spec/README.md`). Reference FR/AC/T IDs in commits, PR bodies and test names.
2. **Decisions live in ADRs** (`docs/adr/`). Read the relevant ADR before proposing an architectural
   change; changing one means a new ADR that supersedes it.
3. **The graph schema has one source:** `packages/core/src/ovas_core/spec.py`. After changing it run
   `make gen`. Never edit `apps/web/src/gen/` or `packages/core/schema/` by hand.
4. **Every query is workspace-scoped** (ADR-0002). A query without `workspace_id` is a bug.
5. **Secrets never leave the server**: not in responses, logs, session events or exports.
6. `make check` must pass before you say a task is done.

## Map

| Path | What | Stack |
| --- | --- | --- |
| `apps/web` | Studio UI | React 19, TS, Vite, TanStack Router/Query, Zustand, React Flow, shadcn (Base UI) |
| `services/api` | Control plane: auth, agents, versions, knowledge, sessions | FastAPI, SQLAlchemy 2 async, Alembic, Postgres + pgvector |
| `services/runtime` | Runs sessions (text now, voice in M2) | FastAPI, WebSocket |
| `packages/core` | `ovas_core`: AgentSpec schema, validation, workflow engine | Pydantic v2 |
| `providers/tts-kokoro` | Kokoro-82M text-to-speech | FastAPI, kokoro-onnx |
| `spec/` | Versioned specs (product, mvp, m0-foundation) | Markdown |
| `docs/` | Architecture, concepts, ADRs | Markdown |

## Commands

```sh
make install      # uv sync + pnpm install
make up           # whole stack in Docker (web :5173, api :8000, runtime :8100, tts :8002)
make dev          # backend in Docker, web with hot reload
make check        # lint + typecheck + gen-check + tests (what CI runs)
make test         # starts the throwaway test DB on 127.0.0.1:55432, runs all tests
make gen          # regenerate schema + TS types from ovas_core
```

New Python dependency: `uv add --package <ovas-api|ovas-core|…> <dep>`. New JS dependency:
`pnpm --filter @ovas/web add <dep>`. Lockfiles change only through these commands.

## Where to look

- Path-scoped rules: `.claude/rules/` (loaded automatically for matching files).
- Package notes: the `CLAUDE.md` inside each package.
- Current work: `spec/mvp/` (highest version) → `tasks.md`.
