---
feature: builder-assistant
title: "Builder assistant: build an agent by chatting"
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-28
updated: 2026-11-28
---

# Builder assistant — Task Backlog

> **Stage 3 · BREAK INTO TASKS.** Vertical slices in dependency order. One PR per slice; each PR
> passes `make check` and `make e2e` and names the tasks and ACs it covers.

## How to use
- Work top to bottom; respect `depends on`.
- A task is **done** only when its linked acceptance criteria pass.
- If a task reveals a spec gap, update `spec.md`/`plan.md` and **bump the version first**.

## Backlog

| # | Task | Serves | Depends on | Verify by | Slice | Done |
| --- | --- | --- | --- | --- | --- | --- |
| T-1 | `ovas_core.assistant`: operation models, `apply_ops` with id rules, `layout_new_nodes`, minimal-change guarantees; unit tests | FR-5, FR-7, FR-8 | — | AC-6, AC-7 | 1 Core | [ ] |
| T-2 | API: threads and proposals tables, thread/accept/reject endpoints, internal context endpoint (draft, documents, tools with secrets as references) | FR-6, FR-10, FR-11 | T-1 | AC-9, AC-10 | 2 Loop | [ ] |
| T-3 | Runtime: assistant WebSocket, prompt builder, structured turn, apply → layout → validate → repair (≤3), proposal storage; stub LLM gains scripted assistant answers | FR-4, FR-5, FR-11 | T-2 | AC-4, AC-10 | 2 | [ ] |
| T-4 | Studio: Assistant panel (streaming chat, quick replies, push-to-talk), ghosts from the proposal diff, change list, Accept (one undo step) and Reject | FR-1, FR-4 | T-3 | AC-3 | 3 Review | [ ] |
| T-5 | Stale proposals: revision check on accept, redo on the new draft | FR-6 | T-4 | AC-5 | 3 | [ ] |
| T-6 | Interview and plan states, "you decide", plan card with confirm; **Describe it** in New agent | FR-1, FR-2, FR-3 | T-4 | AC-1, AC-2 | 4 Interview | [ ] |
| T-7 | Explain: answers with node links that select on the canvas | FR-9 | T-4 | AC-8 | 4 | [ ] |
| T-8 | Evaluation script and 20 briefs; measure NFR-1 and NFR-2 on the default model; E2E (describe → plan → accept → edit → undo) with the stub LLM; docs and CHANGELOG | NFR-1, NFR-2 | all | NFR-1, NFR-2 | 5 Release | [ ] |

## Definition of done (this version)
- [ ] Every functional requirement (FR-1–FR-11) has at least one task.
- [ ] Every acceptance criterion (AC-1–AC-10) has a verifying test.
- [ ] All tasks checked off, `make check` and `make e2e` passing in CI.
- [ ] NFR-1 and NFR-2 measured on the default local model and recorded in the PR.
- [ ] `spec.md` and `plan.md` still match what was built (else bump + reconcile).
