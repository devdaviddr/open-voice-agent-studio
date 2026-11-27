---
feature: tools
title: "Tools: webhooks, secrets and the tool library"
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-28
updated: 2026-11-28
---

# Tools — Task Backlog

> **Stage 3 · BREAK INTO TASKS.** Vertical slices in dependency order. One PR per slice; each PR
> passes `make check` and `make e2e` and names the tasks and ACs it covers.

## How to use
- Work top to bottom; respect `depends on`.
- A task is **done** only when its linked acceptance criteria pass.
- If a task reveals a spec gap, update `spec.md`/`plan.md` and **bump the version first**.

## Backlog

| # | Task | Serves | Depends on | Verify by | Slice | Done |
| --- | --- | --- | --- | --- | --- | --- |
| T-1 | Secrets: table, encrypted write-only API, Settings → Secrets UI, masking helper used by logs and events | FR-1 | — | AC-1 | 1 Library | [ ] |
| T-2 | Tools: table, CRUD and duplicate API, parameter form → JSON Schema, tool editor UI, Tools page | FR-2 | T-1 | AC-2 | 1 | [ ] |
| T-3 | Executor: templates, secret resolution, address checks with pinned transport, 1 MB cap, timeout; Try it API and UI with sample keep | FR-3, FR-14 | T-2 | AC-3, AC-13 | 1 | [ ] |
| T-4 | Engine: workspace tools in the LLM function list, argument validation with one retry, waiting and failure lines, `call_tool` injection | FR-6, FR-9 | T-3 | AC-5, AC-8 | 2 Agents | [ ] |
| T-5 | Internal call endpoint, mock for console sessions, per-session cap; runtime wiring; attach and narrow tools in the builder | FR-6, FR-10, FR-14 | T-4 | AC-5, AC-9, AC-13 | 2 | [ ] |
| T-6 | Console and canvas: tool call rows (args, mock, status, latency, result), "calling <tool>" phase; events stored | FR-13 | T-5 | AC-12 | 2 | [ ] |
| T-7 | Version snapshots: `tool_snapshot` at publish, sessions use it, missing-tool validation, tool changes in the diff view | FR-12 | T-5 | AC-11 | 2 | [ ] |
| T-8 | Tool call node: palette and inspector (args as expressions, result map with picker from the sample), engine execution, `tool.ok` / `tool.status` | FR-7 | T-5 | AC-6 | 3 Flow | [ ] |
| T-9 | Confirm first in the engine (`tool_confirm` event), console display | FR-8 | T-4 | AC-7 | 3 | [ ] |
| T-10 | Built-ins `go_to_node` and `set_variable` | FR-11 | T-4 | AC-10 | 3 | [ ] |
| T-11 | Gallery: templates (DD-6) with setup checklists, "Add from gallery" flow | FR-4 | T-3 | AC-4 | 4 Gallery | [ ] |
| T-12 | Tool stats on the Tools page from session events | FR-5 | T-6 | (manual + API test) | 4 | [ ] |
| T-13 | E2E: gallery → try it (local test server) → attach → console call with mock and live; docs (concepts, getting started), CHANGELOG | NFR-3 | all | NFR-3 | 4 | [ ] |

## Definition of done (this version)
- [ ] Every functional requirement (FR-1–FR-14) has at least one task.
- [ ] Every acceptance criterion (AC-1–AC-13) has a verifying test.
- [ ] All tasks checked off, `make check` and `make e2e` passing in CI.
- [ ] `spec.md` and `plan.md` still match what was built (else bump + reconcile).
