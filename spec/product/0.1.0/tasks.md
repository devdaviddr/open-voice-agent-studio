---
feature: product
title: Open Voice Agent Studio v1
version: 0.1.0
status: draft
updated: 2026-11-27
---

# Open Voice Agent Studio v1 — Task Backlog

> **Stage 3 · BREAK INTO TASKS.** At product level each task is a **milestone**. A milestone
> starts by writing its own spec under `spec/<milestone>/` (Stages 1–3), which breaks it into
> reviewable tasks. Code for a milestone starts only after that spec is approved.

## How to use
- Work top to bottom; respect `depends on`.
- A milestone is **done** when every AC it serves passes and its spec is bumped to `implemented`.
- If a milestone reveals a product-level gap, update this spec and bump its version first.

## Backlog

| # | Milestone | Serves | Depends on | Verify by | Done |
| --- | --- | --- | --- | --- | --- |
| M0 | **Foundation:** monorepo restructure, `ovas-core` schema + TS codegen, Postgres + Alembic baseline, Claude rules/skills/hooks, lefthook, CI, docs, ADRs, contributor files; remove Rust | NFR-7, NFR-6 | — | `spec/m0-foundation` ACs | [ ] |
| M1 | **Builder:** auth and workspaces, agents CRUD, draft graph editor with full node catalogue, validation, publish, environments, diff, pronunciation, settings | FR-1, FR-2, FR-4–FR-13, FR-35 | M0 | AC-1, AC-2, AC-4–AC-13, AC-35 | [ ] |
| M2 | **Voice loop:** runtime + workflow engine on Pipecat, WebRTC, STT service, turn-taking, text mode, console, session history and latency, provider plugins, offline default | FR-14–FR-18, FR-25, FR-26, FR-29, FR-31 | M1 | AC-14–AC-18, AC-25, AC-26, AC-29, AC-31 | [ ] |
| M3 | **Tools:** webhook, MCP, client and built-in tools, per-node narrowing, secrets vault | FR-19–FR-24 | M2 | AC-19–AC-24 | [ ] |
| M4 | **Knowledge and memory:** knowledge base ingestion and search, long-term memory with end-user deletion | FR-27, FR-28 | M2 | AC-27, AC-28 | [ ] |
| M5 | **Ship:** widget SDK with theming and origins, API keys, CLI, OpenTelemetry, retention, docs pass, **v1.0.0** | FR-3, FR-30, FR-32–FR-34 | M3, M4 | AC-3, AC-30, AC-32–AC-34 | [ ] |
| v1.1 | Scenario evaluations (simulated caller + judged criteria, per-version pass rates) | future spec | v1.0 | — | [ ] |
| v2 | Phone (Twilio/SIP), human transfer, A/B splits, custom node plugins, multi-tenant admin | future spec | v1.x | — | [ ] |

## Definition of done (this version)
- [ ] Every functional requirement (FR-N) is served by a milestone. (FR-1–FR-35 mapped above.)
- [ ] Every acceptance criterion (AC-N) is verified inside its milestone's tests.
- [ ] All milestones M0–M5 done and v1.0.0 released.
- [ ] `spec.md` and `plan.md` still match what was built (else bump + reconcile).
