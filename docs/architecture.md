# Architecture

```
 browser ── studio (apps/web, Vite) ──/api──▶ api (services/api) ──▶ Postgres + pgvector
                    │                          │  ├─▶ tts-kokoro  (read-aloud)
                    │                          │  ├─▶ stt-whisper (push-to-talk)
                    │                          │  └─▶ LLM (memory extraction)
                    └──/rt (WebSocket)──▶ runtime (services/runtime) ──▶ LLM (conversation)
                                               └─▶ api /internal (session, events, search)
```

| Part | Path | Role |
| --- | --- | --- |
| Studio | `apps/web` | React 19, TanStack Router and Query, Zustand, React Flow, shadcn on Base UI. Talks only to public API endpoints (ADR-0020). |
| API | `services/api` | Control plane: auth, agents, drafts, versions, knowledge, memories, sessions, settings. FastAPI, async SQLAlchemy, Alembic. Runs the background job worker. |
| Runtime | `services/runtime` | Runs sessions over a WebSocket. Loads the session from the API, drives the engine, streams events, stores them back. |
| Core | `packages/core` | `ovas_core`: the `AgentSpec` schema (the one source of truth, ADR-0008), validation, diff and the workflow engine. Pure: the LLM and lookups are injected. |
| Kokoro | `providers/tts-kokoro` | Text to speech (Kokoro-82M, ONNX). |
| Whisper | `providers/stt-whisper` | Speech to text (faster-whisper, CPU). |
| Database | `db` | Postgres 17 with pgvector (ADR-0010). |

## Data

Every workspace-owned table carries `workspace_id` and every query filters by it (ADR-0002).
Drafts and versions store the `AgentSpec` as JSONB; a trigger keeps versions immutable (ADR-0011).
Knowledge passages and memories are `vector(384)` columns with cosine search. Secrets such as the
LLM key are encrypted with `OVAS_SECRET_KEY` and never returned (ADR-0019).

## A turn

1. The studio asks the API for a session; the API checks the draft is valid, snapshots the spec
   and returns a signed WebSocket URL.
2. The runtime loads the session (spec, variables, LLM settings) from `/internal`.
3. On each caller message the engine builds the prompt (agent prompt, step prompt, known
   variables, remembered facts, optional document passages, a summary of older turns), streams the
   reply, runs any tool calls (`search_knowledge`, `recall_memory`, `end_session`), then evaluates
   the outgoing edges: expressions, then one LLM call for natural-language conditions, then `else`.
4. Events stream to the studio, which animates the canvas, and are stored in batches.
5. When the session ends, the API queues memory extraction if memory is on.

## Background jobs

The API runs an in-process worker over a `jobs` table: knowledge indexing and memory extraction.
Jobs are claimed with `SKIP LOCKED`, retried up to three times, and re-queued after a restart.

## Models

All models are local by default (ADR-0006): the LLM you configure, Kokoro, Whisper and the
`bge-small-en-v1.5` embedding model. Model files download on first use into Docker volumes.

## Quality gates

`make check` (lint, types, generated-code drift, tests with an 80% API coverage floor) and
`make e2e` (Playwright against a throwaway stack with a scripted stub LLM) run on every pull request.
`develop` and `main` only change through pull requests with those checks green (ADR-0016).

See [`docs/adr`](adr) for the decisions behind this, and [`spec/`](../spec) for the requirements.
