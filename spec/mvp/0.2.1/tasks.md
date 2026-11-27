---
feature: mvp
title: "MVP: builder, auth, context and text test console"
version: 0.2.1
status: draft
updated: 2026-11-28
---
# MVP — Task Backlog

> **Stage 3 · BREAK INTO TASKS.** Vertical slices in dependency order. One PR per slice; each PR
> passes `make check` and names the tasks and ACs it covers.

## How to use
- Work top to bottom; respect `depends on`.
- A task is **done** only when its linked acceptance criteria pass.
- If a task reveals a spec gap, update `spec.md`/`plan.md` and **bump the version first**.

## Backlog

| # | Task | Serves | Depends on | Verify by | Slice | Done |
| --- | --- | --- | --- | --- | --- | --- |
| T-1 | Restructure into the monorepo (M0 T-1–T-3): apps/web, services/api, services/runtime, packages/core, providers/tts-kokoro; drop Rust; uv + pnpm workspaces; Makefile | FR-22 | — | AC-20 | 1 Foundation | [x] |
| T-2 | Postgres + pgvector in compose; SQLAlchemy async; Alembic baseline; api `/health` aggregates | FR-22 | T-1 | AC-20 | 1 | [x] |
| T-3 | `ovas-core` AgentSpec models (full product schema), JSON Schema → TS codegen, `gen-check` | FR-22, FR-6 | T-1 | AC-20 | 1 | [x] |
| T-4 | CI workflow, lefthook, root + package CLAUDE.md, AGENTS.md, `.claude/rules`, format-on-edit + guard hooks with tests | FR-22 | T-1 | AC-20 | 1 | [x] |
| T-5 | Auth: users, workspaces, memberships, sessions, argon2id, sign-up/in/out, open sign-up setting, rate limit, Origin/content-type guard | FR-1, FR-2, FR-3 | T-2 | AC-1, AC-2, AC-3 | 2 Auth | [x] |
| T-6 | Web: TanStack Router + Query, generated OpenAPI client, sign-in/sign-up pages, auth guard, app shell (sidebar, theme) | FR-1 | T-5, T-3 | AC-1 (e2e) | 2 | [x] |
| T-7 | Agents API: CRUD, duplicate, from-template (receptionist), draft GET/PUT with revision + 409 | FR-4, FR-7 | T-5 | AC-4, AC-6 | 3 Builder | [x] |
| T-8 | Validation in `ovas-core` (graph rules, CEL parse, variable references) + `/validate` | FR-8 | T-3 | AC-7 | 3 | [x] |
| T-9 | Builder UI layout A: palette, canvas (MVP node types, condition edges), inspector per node/edge, agent settings, variables panel | FR-5, FR-6, FR-9, FR-13 (declare) | T-6, T-7 | AC-5 | 3 | [x] |
| T-10 | Builder state: Zustand + zundo undo/redo, shortcuts, copy/paste, autosave with conflict dialog, validation overlay | FR-7, FR-8, FR-10 | T-9, T-8 | AC-6, AC-7, AC-9 | 3 | [x] |
| T-11 | Versions: publish, list, read-only view, restore, live pointer; immutability trigger | FR-11 | T-7 | AC-10 | 4 Versions | [x] |
| T-12 | Structural diff in `ovas-core` + `/diff` + diff view in the versions panel | FR-12 | T-11 | AC-11 | 4 | [x] |
| T-13 | Settings: LLM provider (encrypted key, test connection); `OVAS_SECRET_KEY` handling | FR-21 | T-5 | AC-19 | 5 Engine | [x] |
| T-14 | Engine in `ovas-core`: node execution, variable templating, Extract with typed validation, edge evaluation (CEL → batched LLM → else), history budget + summary | FR-13, FR-14, FR-9 | T-3, T-8 | AC-8, AC-12, AC-13 | 5 | [x] |
| T-15 | Runtime: session token, WebSocket stream protocol, event persistence via internal API; `POST /sessions`, sessions list/detail API | FR-17, FR-20 | T-14, T-13 | AC-16, AC-18 | 5 | [x] |
| T-16 | Console UI: slide-out panel, streaming chat, event timeline, active-node highlight, test end-user ID, read-aloud via `/tts` | FR-17, FR-18, FR-19 | T-15, T-10 | AC-16, AC-17 | 5 | [x] |
| T-17 | Sessions page: list + transcript/events view | FR-20 | T-15 | AC-18 | 5 | [x] |
| T-18 | Jobs table + in-process worker; knowledge upload, parse (md/txt/pdf), chunk, embed (fastembed), status | FR-15 | T-2 | AC-14 | 6 Knowledge | [x] |
| T-19 | `search_knowledge` tool + auto top-k in engine; knowledge page + attach/narrow in builder | FR-15 | T-18, T-14, T-9 | AC-14 | 6 | [x] |
| T-20 | Memory: extraction job on session end, recall at start, `recall_memory` tool, memories UI with delete | FR-16 | T-18, T-15 | AC-15 | 7 Memory | [ ] |
| T-21 | Playwright e2e (sign-up → template → edit → publish → chat → memory) with stub LLM; coverage gate ≥ 80% | NFR-1 | all | NFR-1 | 8 Release | [ ] |
| T-23 | `providers/stt-whisper` (faster-whisper, `/health`, `/stt`), compose service + model volume, API `/v1/stt` proxy | FR-23 | T-1, T-5 | AC-21 | 9 Voice | [x] |
| T-24 | Console push-to-talk: mic button, recording state, 60 s cap, transcript sent as the caller's turn, errors | FR-23 | T-23, T-16 | AC-21 | 9 | [x] |
| T-25 | Canvas activity: per-node phase (waiting, thinking, speaking, tool), animated firing edge, visited trail, reduced motion | FR-24 | T-16 | AC-22 | 9 | [x] |
| T-22 | Docs: README, getting started, concepts, architecture; CHANGELOG; release 0.3.0; bump spec to implemented | FR-22 | all | AC-20 | 8 | [ ] |

## Definition of done (this version)
- [ ] Every functional requirement (FR-1–FR-24) has at least one task.
- [ ] Every acceptance criterion (AC-1–AC-22) has a verifying test.
- [ ] All tasks checked off, `make check` and e2e passing in CI.
- [ ] `spec.md` and `plan.md` still match what was built (else bump + reconcile).