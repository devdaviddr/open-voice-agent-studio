---
feature: tools
title: "Tools: webhooks, secrets and the tool library"
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-28
updated: 2026-11-28
---

# Tools — Implementation Plan

> **Stage 2 · PLAN.** Built on `spec/product/1.0.0/plan.md`, ADR-0011 (snapshots), ADR-0012 (tool
> types) and ADR-0019 (write-only secrets).

## 1. Approach summary

Tools and secrets live in the API. **The API executes every tool call**: the runtime asks it to,
so secrets are decrypted and SSRF checks run in one place, and the runtime never holds a secret.
The engine in `ovas-core` stays pure: it receives the tool definitions with the session and an
injected `call_tool` function, and owns the conversational rules (argument validation, confirm
first, waiting lines, Tool call node, built-ins).

## 2. Technology choices

| Concern | Choice | Why |
| --- | --- | --- |
| HTTP calls | `httpx.AsyncClient` with a custom transport that pins the resolved, checked IP | Prevents DNS-rebinding past the address check |
| Templates | A tiny `{{…}}` renderer shared with prompts (`ovas_core.engine.render`), JSON-escaped in bodies | One syntax users already know |
| Argument validation | `jsonschema` (Draft 2020-12) in `ovas-core` | Same validation for LLM calls and Try it |
| JSONPath for result maps | `jsonpath-ng` | Small, maintained, enough for `$.slots[0].start` |
| Expressions for Tool call args | Existing CEL evaluator | Same language as edge conditions |
| Parameter form → schema | Studio component; schema stored as JSON Schema | Builders never edit JSON; power users still can |

## 3. Architecture

```
studio ─ /v1/secrets, /v1/tools, /v1/tools/{id}/try ─▶ api ── executor ──▶ service
runtime ─ /internal/sessions/{id}/tools/{tool}/call ─▶ api ── executor ──▶ service (or mock)
engine (in runtime): tools list for the LLM, arg validation, confirm first, Tool call node
```

- `ovas_api.tools.executor`: render templates (params, variables, secrets), check URL scheme and
  resolved address against the deny list and `OVAS_TOOL_ALLOWED_HOSTS`, send with the pinned
  transport, cap the body at 1 MB, time out, and return `{ok, status, latency_ms, body}` plus a
  masked copy of the request. One code path for Try it and sessions.
- `POST /internal/sessions/{id}/tools/{tool_id}/call`: looks the tool up in the session's snapshot
  (version) or the workspace (draft), applies mock for console sessions, enforces the per-session
  cap, returns the result. The session's workspace scopes everything (ADR-0002).
- Engine: `TextSession` gets `tools: dict[str, ToolDef]` and `call_tool(tool_id, args)`. Workspace
  tools join the function list for the LLM next to built-ins. Before executing: validate arguments;
  if `confirm`, return an instruction to read back and ask, record a pending confirmation, and only
  execute when the LLM calls again after a new caller turn; emit the waiting line as an assistant
  message part; on failure return `{ok: false, status, failure_message}`.
- Tool call node: evaluate argument expressions, call, write the result map into variables
  (type-checked like Extract), set `tool.ok` / `tool.status`, then take edges as usual.
- Built-ins `go_to_node` and `set_variable` implemented in the engine.

## 4. Data & contracts

Tables: `secrets` (workspace_id, name, value_encrypted, last_used_at; unique name per workspace),
`tools` (workspace_id, name unique per workspace, definition JSONB, sample JSONB, mock JSONB),
`agent_versions.tool_snapshot` JSONB (migration adds it, default `{}`).

REST (all `/v1`, cookie auth):

```
GET|POST /secrets   PUT|DELETE /secrets/{name}            (owner only; values never returned)
GET|POST /tools     GET|PATCH|DELETE /tools/{id}   POST /tools/{id}/duplicate
POST /tools/{id}/try {arguments}                            GET /tools/templates
GET /tools/{id}/stats?days=7
POST /internal/sessions/{id}/tools/{tool_id}/call {arguments, node_id}   (runtime)
```

## 5. Key decisions & trade-offs

- **DD-1.** The API, not the runtime, executes calls, so secrets and network checks live in one
  process. Cost: one extra local hop (well under NFR-2's 50 ms).
- **DD-2.** Snapshots are stored next to the version (`tool_snapshot`), not inside `AgentSpec`, so
  the spec schema and the diff stay about the agent; the diff view shows tool definition changes
  separately.
- **DD-3.** Confirm first is enforced by the engine, not by prompt wording alone: an LLM that skips
  the read-back still cannot trigger the call.
- **DD-4.** Mock is a per-tool console switch (OQ-2): simple to reason about, never active for real
  callers.
- **DD-5.** Tool results go back to the LLM truncated to 8 KB of JSON; the console and events keep
  2 KB. Large payloads should be narrowed with the result map.
- **DD-6.** First gallery (OQ-1): Cal.com find free slots; Cal.com book a slot; HubSpot find contact
  by phone or email; Twilio send SMS; Slack post a message (incoming webhook); Zendesk create a
  ticket; Shopify order status; Airtable create a record; plus "Blank webhook". Each is a JSON file
  in `services/api/src/ovas_api/tools/templates/` with a setup checklist.

## 6. Risks & mitigations

- **Risk:** Small local models call tools with wrong or missing arguments. **Mitigation:** schema
  validation with one corrective retry; parameter descriptions shown to the LLM; the console shows
  exactly what was sent.
- **Risk:** SSRF on self-hosted installs. **Mitigation:** deny private ranges after resolution,
  pin the resolved IP, allowlist only by operator env var, tests for each range (AC-13).
- **Risk:** Gallery templates drift from the services' APIs. **Mitigation:** templates are data,
  each with a docs link; Try it shows failures plainly.

## 7. Rollout & observability

Four slices (see `tasks.md`), one PR each, each green on `make check` and `make e2e`. Tool calls are
session events, so Sessions and the Tools page stats are the observability. Release as 0.4.0.
