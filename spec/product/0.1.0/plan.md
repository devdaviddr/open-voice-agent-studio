---
feature: product
title: Open Voice Agent Studio v1
version: 0.1.0
status: draft
updated: 2026-11-27
---

# Open Voice Agent Studio v1 — Implementation Plan

> **Stage 2 · PLAN.** The architecture for everything in `spec.md`. Each decision links to an ADR in
> `docs/adr/`, which holds the full context and the alternatives rejected.

## 1. Approach summary

A monorepo with a TypeScript studio and a Python backend split into two processes: a **control
plane API** (accounts, agents, versions, tools, knowledge) and a **runtime** (live sessions). The
runtime compiles a published `AgentSpec` into a Pipecat pipeline whose LLM context is driven by a
workflow engine that walks the graph. The workflow schema is defined once in Pydantic and generated
into TypeScript, so the builder and the runtime cannot disagree. Providers are local by default and
pluggable.

The key bet: Pipecat already solves the hard real-time problems (VAD, turn-taking, interruptions,
transports, dozens of providers), so our work goes into the studio, the workflow engine and the
versioning, which is what nobody offers in the open.

## 2. Technology choices

| Area | Choice | Why | Alternative considered | ADR |
| --- | --- | --- | --- | --- |
| Deployment | Self-hosted, one workspace per install, `workspace_id` everywhere | Ship fast; multi-tenant later without a rewrite | Multi-tenant from day one | 0002 |
| Graph model | Conversation workflow (FR-5) | What voice-agent builders need; pipeline lives in settings | Component pipeline graph | 0003 |
| Edge expressions | CEL (`cel-python`; a JS CEL library picked in M1 against a shared conformance suite) | Safe, typed, same semantics in Python and TS | JSONLogic, JS eval | 0003 |
| Voice runtime | Pipecat + SmallWebRTCTransport | VAD, smart-turn, interruptions, providers built in; no media server | LiveKit Agents, custom | 0004 |
| Rust | Removed | No job for it yet | Keep placeholder | 0005 |
| Providers | Local defaults behind a plugin interface (entry points `ovas.providers`) | Offline by default, open to any vendor | Cloud-first | 0006 |
| Process | Spec-driven development, ADRs | Versioned contract; decisions not re-litigated | Ad hoc issues | 0007 |
| Repo | pnpm + uv workspaces; schema in Pydantic → JSON Schema → TS | One source of truth for the graph | Separate repos; schema in TS | 0008 |
| Topology | Separate `api` and `runtime` processes sharing `ovas-core` | Different scaling and failure modes | One process | 0009 |
| Database | Postgres 17 + pgvector, SQLAlchemy 2, Alembic | Relational + vector in one store | SQLite + separate vector DB | 0010 |
| Versioning | Draft → immutable versions → environment pointers | Safe change, traceable sessions | Git branches | 0011 |
| Tools | Webhook, MCP, client, built-in | Covers server, page and protocol integrations | Webhook only | 0012 |
| Auth | Local accounts, argon2id, cookie sessions; API keys; widget public keys + origins | Simple self-host; OIDC later | OIDC only | 0013 |
| Frontend | Vite SPA, TanStack Router/Query, Zustand, React Flow 12, shadcn (Base UI), Vitest | No SSR need; fast; typed | Next.js | 0014 |
| Channels | Console, text mode, widget (web component) | Test + embed; phone in v2 | Phone in v1 | 0015 |
| Quality gates | lefthook, Claude Code hooks, GitHub Actions on PRs | Same checks for humans, agents and CI | Local only | 0016 |
| Context | Variables, history budget, opt-in memory, pgvector knowledge base (fastembed) | Clear, separately controllable layers | One memory blob | 0017 |
| Observability | Session events in Postgres, OpenTelemetry export, retention settings | Debuggable and private | Bundled tracing stack | 0018 |
| Secrets | AES-GCM with `OVAS_SECRET_KEY`, write-only API | Never leak keys | Plain env vars per tool | 0019 |
| Agents as code | REST parity + `ovas` CLI with YAML | Git review of agents | UI only | 0020 |

## 3. Architecture

```
 Browser ──────────────────────────────────────────────────────────────────────────
   apps/web (studio)                    packages/widget (<ovas-agent> web component)
     │ REST (OpenAPI client)              │ REST: start session        │ WebRTC
     ▼                                    ▼                            │
 services/api  (FastAPI, control plane) ◄─┘                            │
   accounts · agents · versions · tools · secrets · knowledge ·        │
   sessions read API · widget keys · OpenAPI                           │
     │ SQLAlchemy                          ▲ session events             │
     ▼                                     │                            ▼
 Postgres 17 + pgvector  ◄─────────────── services/runtime  (Pipecat, one pipeline per session)
                                             workflow engine ── tools (webhook · MCP · client · built-in)
                                             │ provider interface (ovas.providers entry points)
                         ┌───────────────────┼──────────────────────┐
                         ▼                   ▼                      ▼
                 providers/stt-whisper  providers/tts-kokoro   LLM: any OpenAI-compatible
                 (faster-whisper)       (Kokoro-82M ONNX)      (optional Ollama profile)
```

- **packages/core (`ovas-core`)**: Pydantic models for `AgentSpec`, nodes, edges, tools, variables;
  graph validation (FR-7); CEL evaluation; JSON Schema export. Imported by api and runtime.
- **apps/web**: studio. Builder state in Zustand, server state in TanStack Query, generated API
  client, generated graph types from `ovas-core`'s JSON Schema.
- **services/api**: owns the database schema and migrations. Publishes versions, issues session
  tokens for the runtime, serves session history.
- **services/runtime**: accepts a session token (agent, version, variables), loads the frozen spec,
  builds a Pipecat pipeline, runs the workflow engine, writes events. Stateless between sessions.
- **providers/**: model servers run as their own containers (heavy dependencies, GPU placement);
  the runtime reaches them through thin Pipecat services implementing the provider interface.
- **packages/cli (`ovas`)**: Python CLI over the REST API.

### Workflow engine (runtime)

Each session holds `current_node`, the variable store and history. On entering an Agent step, the
engine sets the LLM system prompt (agent prompt + node prompt, variables rendered), the tool list
(narrowed), and provider overrides. After each assistant turn it evaluates outgoing edges in order:
CEL edges first, then one batched LLM judgement over the LLM edges, then `else`. Extract, Router,
Tool call, Handoff and End run without speaking. Built-in `go_to_node` lets the LLM jump explicitly.

## 4. Data & contracts

Database tables mirror spec §7 one-to-one, all with `workspace_id` and a composite index on it.
`agent_versions.spec` is JSONB and immutable (enforced by a trigger and by the API).
`memories.embedding` and `knowledge_chunks.embedding` are `vector(384)` (bge-small-en-v1.5).

REST (prefix `/v1`, bearer API key or session cookie):

```
POST   /auth/signup | /auth/login | /auth/logout          GET /me
GET    /agents                POST /agents                GET|PATCH|DELETE /agents/{id}
POST   /agents/{id}/duplicate
GET|PUT /agents/{id}/draft     POST /agents/{id}/draft/validate
POST   /agents/{id}/versions   (publish)   GET /agents/{id}/versions[/{n}]
GET    /agents/{id}/diff?from=&to=
PUT    /agents/{id}/environments/{env}   { version }
CRUD   /tools  /mcp-servers  /secrets (write-only)  /knowledge  /widgets  /api-keys
POST   /sessions   { agent_id, environment|version|draft, mode, variables, end_user_id } → { session_id, runtime_url, token }
GET    /sessions   GET /sessions/{id}   GET /sessions/{id}/events   DELETE /sessions/{id}
GET|DELETE /memories?agent_id=&end_user_id=
```

Runtime: `POST {runtime_url}/offer` (WebRTC SDP exchange, authorised by the session token),
`WS {runtime_url}/text` for text mode, data channel messages for console events and client tools.

## 5. Key decisions & trade-offs

- **DD-1.** Snapshots, not references: a version copies tool and knowledge configuration it uses, so
  editing a tool later does not change a published agent. Secrets stay references.
- **DD-2.** One batched LLM call judges all LLM-conditioned edges of a node, keeping transitions to at
  most one extra call per turn.
- **DD-3.** Model servers are separate containers; the runtime holds no model weights.
- **DD-4.** Studio talks only to the public REST API; no private endpoints (FR-34).
- **DD-5.** The graph schema version (`schema_version`) is independent of the app version; the
  runtime keeps readers for every released schema version (NFR-8).

## 6. Risks & mitigations

- **Risk:** CPU-only latency too slow for natural conversation. **Mitigation:** measure per turn from
  M2; smallest models by default; GPU auto-detect; streaming everywhere.
- **Risk:** Pipecat API churn. **Mitigation:** pin the version; wrap it behind our pipeline builder so
  upgrades touch one module.
- **Risk:** LLM-judged edges are unreliable. **Mitigation:** CEL first; show edge decisions in the
  console; evaluations in v1.1.
- **Risk:** Scope is large for v1. **Mitigation:** milestones each ship something usable; anything not
  in an approved milestone spec waits.
- **Risk:** MCP stdio servers run arbitrary commands. **Mitigation:** stdio is operator-only
  configuration (env/config file), not editable from the UI; UI adds HTTP MCP servers only.

## 7. Rollout & observability

- Milestones M0–M5 (see `tasks.md`), each with its own approved spec, merged through PRs.
- Semantic versioning of the app from 0.1.0; v1.0.0 at the end of M5. `CHANGELOG.md` per release.
- Session latency and errors are visible in the studio from M2 (FR-31); OTel export in M5.
- Rollback for operators: images are tagged per release; Alembic migrations are reversible within a
  minor series.
