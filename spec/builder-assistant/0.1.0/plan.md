---
feature: builder-assistant
title: "Builder assistant: build an agent by chatting"
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-28
updated: 2026-11-28
---

# Builder assistant — Implementation Plan

> **Stage 2 · PLAN.** Architecture decided in ADR-0021 (proposed with this plan).

## 1. Approach summary

The assistant is an LLM conversation that answers each turn with structured output: a message,
optional quick replies, and optionally a list of graph operations. The operations are applied to a
copy of the draft by pure code in `ovas-core`, laid out, validated, and repaired in a loop; the
result is a **proposal** the studio shows as ghosts. Only when the user accepts does the studio
save the new draft through the normal draft API, so autosave, conflicts, undo and versions behave
exactly as for manual edits.

## 2. Technology choices

| Concern | Choice | Why |
| --- | --- | --- |
| Where it runs | The runtime, on a new WebSocket `/v1/assistant/{agent_id}/stream` | The runtime already streams LLM conversations and has the LLM client; the studio already proxies `/rt` |
| Model output | One structured response per turn (`json_schema`, falling back to `json_object`) with an `ops` array | More reliable on small local models than many parallel tool calls |
| Operations, layout, validation | `ovas_core.assistant` (pure): `apply_ops`, `layout_new_nodes`, existing `validate` and `diff` | Testable without an LLM; same code for server and tests |
| Ghosts | Studio diffs the current flow against the proposal's resulting spec (existing diff) | No second implementation of the operations in TypeScript |
| Storage | API tables `assistant_threads`, `assistant_proposals`; runtime reads and writes them via `/internal` | Same split as sessions |

## 3. Architecture

```
studio Assistant panel ─/rt WS─▶ runtime assistant loop ──▶ workspace LLM
        ▲  proposal (ops + resulting spec + diff)   │  apply_ops → layout → validate → repair (≤3)
        │                                           ▼
        └── Accept: PUT /v1/agents/{id}/draft (base revision) ── api ── assistant_* tables via /internal
```

Turn loop:
1. Load thread, current draft (with revision), document names, tool definitions (secrets as
   references) from the API.
2. Build the prompt: role and rules, node catalogue with one example each, the current draft in a
   compact form (ids, labels, prompts, conditions, variables), interview state, the user's message.
3. Ask the LLM for `{message, quick_replies?, plan?, ops?}`.
4. If `ops`: `apply_ops` to a copy → `layout_new_nodes` → `validate` (with knowledge and tool ids).
   On errors, send the issues back ("these problems remain, return corrected ops") up to three
   times. Store the proposal with `base_revision`, the resulting spec and remaining issues.
5. Stream the message, quick replies, plan or proposal to the studio.

Interview mode is a state in the thread (`interviewing` → `planned` → `building` → `editing`), so
the assistant asks before building only for new or empty agents (FR-2) and goes straight to
proposals for edits.

## 4. Data & contracts

Tables: `assistant_threads` (workspace_id, agent_id, user_id, state, messages JSONB),
`assistant_proposals` (workspace_id, thread_id, base_revision, ops JSONB, spec JSONB, issues JSONB,
summary, status).

```
GET|DELETE /v1/agents/{id}/assistant              thread for the current user (clear = DELETE)
POST /v1/agents/{id}/assistant/proposals/{pid}/accept {revision}  → marks accepted after the studio saved
POST /v1/agents/{id}/assistant/proposals/{pid}/reject
WS   /rt/v1/assistant/{agent_id}/stream?token=…   (token from POST /v1/agents/{id}/assistant/session)
/internal/assistant/...                           thread, draft context, store proposal (runtime)
```

## 5. Key decisions & trade-offs

- **DD-1.** Operation set as in spec §7. `add_node` ids are prefixed by the assistant
  (`ast-<slug>`) and made unique by `apply_ops`; unknown ids in other operations are errors fed
  back to the LLM.
- **DD-2.** Proposals carry the resulting spec, so the studio never re-implements operations; the
  operations are kept for display ("Added Extract 'Email'") and for AC-6 checks.
- **DD-3.** Layout: new nodes go in the column after their first incoming neighbour (320 px apart),
  in the first free row (140 px apart) that does not overlap existing nodes. Existing nodes never
  move (FR-8); "tidy up" is a separate operation the user asks for.
- **DD-4.** Stale proposals (FR-6): accept sends the proposal's `base_revision`; a 409 from the
  draft API marks it stale and the studio asks the assistant to redo it on the new draft.
- **DD-5.** Not built as an OVAS agent on the existing engine (considered, see ADR-0021): the engine
  is shaped for spoken turns and step routing, not long structured tool loops. Revisit when the
  engine gains a text-first mode.
- **DD-6.** Evaluation (NFR-2): `scripts/assistant_eval.py` runs 20 briefs from
  `spec/builder-assistant/eval/briefs.json` against a configured LLM and reports valid-first-try,
  repaired and failed counts. Not in CI; CI runs the stub LLM, extended with scripted assistant
  answers.

## 6. Risks & mitigations

- **Risk:** Small models produce invalid operations or JSON. **Mitigation:** strict schema,
  compact context, worked examples from the templates, the repair loop, NFR-2 measured on the real
  default model before release.
- **Risk:** Large drafts blow the context. **Mitigation:** compact draft form (no positions, prompts
  truncated with a marker); the assistant can ask to see a node in full via a read operation.
- **Risk:** Users accept changes they did not read. **Mitigation:** ghosts plus a change list in
  plain words; one undo restores everything.

## 7. Rollout & observability

Five slices (see `tasks.md`). Proposals and their status are stored, so acceptance rate and repair
counts can be read from the database. Ships after tools slice 1–2 so the assistant can attach and
draft tools. Release as 0.5.0.
