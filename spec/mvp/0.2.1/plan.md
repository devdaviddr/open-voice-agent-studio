---
feature: mvp
title: "MVP: builder, auth, context and text test console"
version: 0.2.1
status: draft
updated: 2026-11-28
---
# MVP — Implementation Plan

> **Stage 2 · PLAN.** Built on the architecture in `spec/product/0.1.0/plan.md` and ADRs 0001–0020.
> This file adds only the MVP-specific choices.

## 1. Approach summary

Lay the M0 foundations first (layout, database, schema codegen, checks, CLAUDE.md), then build
vertical slices that each end in something a user can do: sign in → manage agents → edit and save a
graph → publish and diff → chat with it → give it knowledge → give it memory. The workflow engine
lives in `ovas-core` so the runtime and the tests share it; the runtime hosts text sessions over
WebSocket now and adds Pipecat voice in M2 without changing the engine.

## 2. Technology choices

| Area | Choice | Why | Alternative considered |
| --- | --- | --- | --- |
| Password hashing | `argon2-cffi` (argon2id) | Current OWASP recommendation | bcrypt |
| Auth sessions | Server-side `user_sessions` table, random 256-bit token, SHA-256 stored | Revocable, no JWT pitfalls | JWT |
| Rate limiting | Postgres-backed counter table | No Redis in the MVP | Redis, in-memory (lost on restart) |
| LLM client | `openai` Python SDK with custom `base_url` | Works with Ollama, Strata, vLLM, OpenAI | Raw httpx |
| CEL | `cel-python` (server, authoritative); validation errors from the API | One implementation in the MVP; JS CEL only needed for live editor hints later | JS + Python from day one |
| Embeddings | `fastembed` `BAAI/bge-small-en-v1.5` (384-d, ONNX, CPU) | Local, small, good quality | sentence-transformers (heavy torch) |
| PDF text | `pypdf` | Pure Python | unstructured (heavy) |
| Chunking | 800-token windows, 100 overlap, Markdown-heading aware | Simple and adequate | semantic chunking |
| Background jobs | In-process asyncio task queue in the API backed by a `jobs` table (indexing, memory extraction) | No broker needed; survives restart by re-queuing `pending` rows | Celery/RQ |
| Frontend data | TanStack Query + `openapi-fetch` with types from `openapi-typescript` | Typed client generated from FastAPI | Hand-written fetch |
| Builder state | Zustand store with `zundo` for undo/redo | Small, works with React Flow | Redux |
| Diff | Server-side structural diff in `ovas-core`; prompt diffs with `difflib` | Same logic for UI and CLI later | Client-side |
| E2E | Playwright against the compose stack with a stub LLM server | Deterministic in CI | Real LLM in CI |
| Default LLM (dev) | Host Ollama, `qwen3.5:9b`, via `host.docker.internal:11434/v1` | Already on the main dev machine | Bundled Ollama container (optional profile kept) |

## 3. Architecture

```
apps/web ──REST (cookie)──► services/api ──SQLAlchemy──► Postgres + pgvector
    │                          │  auth · agents · versions · diff · knowledge · memories ·
    │                          │  sessions (create, list, read) · settings · jobs
    └──WebSocket (session token)──► services/runtime
                                     └─ ovas_core.engine.TextSession
                                          ├─ LLM (OpenAI-compatible)
                                          ├─ knowledge + memory search (via API internal endpoints)
                                          └─ writes events through the API's internal endpoint
apps/web ──REST──► providers/tts-kokoro (read-aloud, proxied through the API at /v1/tts)
```

- `POST /v1/sessions` (API, cookie auth) creates the session row, freezes which spec it runs
  (version or current draft revision), and returns a short-lived signed token and the runtime URL.
- The runtime verifies the token (HMAC with `OVAS_INTERNAL_KEY`), fetches the spec and LLM config
  from the API's internal endpoints, runs `TextSession`, and posts events back.
- Internal endpoints (`/internal/*`) listen on the API's internal network only and require
  `OVAS_INTERNAL_KEY`.

### Engine turn loop (`ovas_core.engine`)

1. Enter node → emit `node_enter`. Start: send first message. Extract/Router/End: run without
   speaking and transition.
2. Agent step: build messages = system(agent prompt + node prompt + recalled memories + auto-top-k
   knowledge, variables rendered) + history (budgeted); tools = `search_knowledge`,
   `recall_memory`, `end_session` as enabled; stream tokens; execute tool calls and loop.
3. After the assistant message: evaluate outgoing edges in order — CEL first, then one JSON-mode
   LLM call that judges all LLM conditions at once, then `else`. Emit `edge`, move, repeat from 1.
4. On end: emit `ended`; if memory is on, enqueue memory extraction.

## 4. Data & contracts

Tables: `workspaces`, `users`, `memberships`, `user_sessions`, `login_attempts`, `agents`,
`agent_versions` (JSONB `spec`, immutable via trigger), `knowledge_sources`, `knowledge_chunks`
(`vector(384)`, HNSW index), `memories` (`vector(384)`), `sessions`,
`session_events`, `llm_providers` (encrypted key), `jobs`.

REST (all `/v1`, cookie auth, JSON):

```
POST /auth/signup  POST /auth/login  POST /auth/logout  GET /me
GET|PATCH /settings (open_signup)       GET|PUT /settings/llm   POST /settings/llm/test
GET|POST /agents {name, template: blank|receptionist}   GET|PATCH|DELETE /agents/{id}   POST /agents/{id}/duplicate
GET /agents/{id}/draft   PUT /agents/{id}/draft {revision, spec} → 200 | 409
POST /agents/{id}/validate   POST /agents/{id}/versions {message}   GET /agents/{id}/versions[/{n}]
POST /agents/{id}/versions/{n}/restore   PUT /agents/{id}/live {version}
GET /agents/{id}/diff?from=draft|N&to=N
GET|POST /knowledge (multipart upload)   GET|DELETE /knowledge/{id}   POST /knowledge/{id}/reindex
POST /internal/sessions/{id}/knowledge/search {query, source_ids?, k} (runtime; attached sources only)
GET|DELETE /agents/{id}/memories?end_user_id=
POST /sessions {agent_id, target: "draft"|N, end_user_id?, variables?} → {session_id, runtime_ws_url, token}
GET /sessions?agent_id=   GET /sessions/{id}   GET /sessions/{id}/events
POST /tts → audio/wav (proxy to providers/tts-kokoro)
POST /stt (raw audio body, ?language=) → {text, language, duration_ms} (proxy to providers/stt-whisper)
```

## 5. Key decisions & trade-offs

- **DD-1.** Tool call and Handoff nodes stay out of the schema's MVP UI but remain in `ovas-core` so
  M3 adds UI and engine handlers without a schema migration.
- **DD-2.** Agents attach knowledge sources in `AgentSpec.knowledge` (no join table), so versions
  snapshot the attachment with the spec. A source's content never changes after upload (there is
  no replace endpoint; re-indexing reuses the stored file), so its ID pins the content without a
  hash. Deleting a source a published version uses is blocked (409) until no version uses it;
  a draft that uses a deleted source shows `missing_knowledge`.
- **DD-3.** One LLM provider per workspace in the MVP; the provider plugin interface lands in M2.
- **DD-5.** Push-to-talk (FR-23) records a whole clip with `MediaRecorder` (webm/opus or mp4,
  whatever the browser makes) and posts it once; Whisper decodes it with PyAV. No streaming, VAD or
  WebRTC: those come with Pipecat in M2 (ADR-0004), which will reuse the same provider.
- **DD-6.** `providers/stt-whisper` uses faster-whisper (CTranslate2, int8 on CPU), model
  `OVAS_WHISPER_MODEL` (default `base`, multilingual), downloaded on first use into a volume. It
  mirrors `providers/tts-kokoro`: its own FastAPI app, reached only through the API.
- **DD-7.** Canvas activity (FR-24) is derived in the studio from the existing runtime events
  (`node_enter`, `edge`, `token`, `assistant_message`, `tool_call`, `knowledge`, `memory`) plus the
  console's own sends and read-aloud playback; the runtime protocol does not change.
- **DD-4.** The engine is synchronous per session (one turn at a time); concurrency comes from many
  sessions, not parallel turns.

## 6. Risks & mitigations

- **Risk:** Small local models handle tool calls and JSON edge-judging poorly. **Mitigation:**
  constrained JSON (`response_format` json_schema where supported, else retry once with a repair
  prompt); console shows each decision; default model qwen3.5:9b tested in a smoke suite.
- **Risk:** fastembed model download in containers. **Mitigation:** cache in a volume, download at
  first use, documented offline pre-fetch command.
- **Risk:** Whisper on CPU is slow for long clips. **Mitigation:** `base` model by default,
  clips capped at 60 s in the browser and 10 MB at the API; model is configurable.
- **Risk:** MVP is a large slice. **Mitigation:** vertical slices, one PR each, each shippable.

## 7. Rollout & observability

- One PR per slice (see `tasks.md`), each green on `make check` and its ACs.
- Release **0.3.0** when every AC passes and the end-to-end test is green; bump this spec to
  `implemented`.
- Console events and stored sessions are the observability for the MVP.