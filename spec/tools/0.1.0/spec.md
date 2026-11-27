---
feature: tools
title: "Tools: webhooks, secrets and the tool library"
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-28
updated: 2026-11-28
---

# Tools — Specification

> **Stage 1 · SPECIFY.** The first slice of product milestone M3. It implements product FR-19
> (webhook tools), FR-22 (built-ins), FR-23 (attach and narrow) and FR-24 (secrets), and the Tool
> call node from product FR-6. MCP servers (product FR-20) and client tools (FR-21) come later.

## 1. Problem & context

Agents built in the MVP can talk, look things up in documents and remember callers, but they cannot
*do* anything: check a calendar, book a slot, look up an order, send a text. Every useful
receptionist, support or booking agent needs that. Today a builder would have to fork the engine.

Builders are not all developers. Many know which service they use (Cal.com, HubSpot, Twilio) and
have an API key, but have never written a JSON Schema. Tools have to be quick to set up from a
known service, safe to try without side effects, and easy to see working in the console.

## 2. Goals

- A builder connects a known service from the gallery, tries it, attaches it to an agent and sees
  the agent use it in the console, in under ten minutes and without writing JSON by hand.
- Tool calls are visible and debuggable: every request and response shows in the console and the
  session, with secrets masked.
- Tools are safe by default on a self-hosted install: secrets never leak, tools cannot reach the
  host's private network unless the operator allows it, and risky actions wait for the caller's yes.
- Published versions keep working exactly as published when a tool is later edited.

## 3. Non-goals

- MCP servers (product FR-20): the next version of this spec.
- Importing tools from OpenAPI documents or cURL commands: next version.
- OAuth sign-in to services (for example Google Calendar); API keys and tokens only.
- Client tools that run in the embedding page (product FR-21): with the widget in M5.
- Handoff nodes, streaming tool responses, automatic retries beyond one.

## 4. User scenarios

- As a **builder**, I open **Tools → Add from gallery**, pick "Cal.com: find free slots", paste my
  API key into the secret it asks for, press **Try it**, and see real slots come back.
- As a **builder**, I attach that tool to my receptionist and ask in the console "Do you have
  anything Tuesday afternoon?"; the step shows "calling Cal.com", the agent says "Let me check the
  diary", then offers the slots it found.
- As a **builder**, I turn on **mock** for "Cal.com: book a slot" so I can test the whole booking
  conversation without creating real bookings.
- As a **builder**, I mark "book a slot" **confirm first**; the agent reads the booking back and
  only books after the caller says yes.
- As a **builder**, I add a **Tool call** node after the booking step that always sends a
  confirmation SMS with the booking time from my variables, and route on whether it succeeded.
- As a **workspace owner**, I rotate an API key by replacing the secret's value; no tool changes.

## 5. Functional requirements

### Secrets
- **FR-1.** Workspace owners MUST be able to create, replace and delete secrets. A secret has a
  name (`UPPER_SNAKE_CASE`, unique per workspace) and a value that is write-only: no API response,
  log line, session event or export contains it. Tools reference secrets as `{{secrets.NAME}}` in
  the URL, headers and body; they are resolved only server-side at call time. (product FR-24)

### Tool library
- **FR-2.** Users MUST be able to create, edit, duplicate and delete webhook tools in the
  workspace. A tool has: a name (`snake_case`, unique per workspace), a "when to use it"
  description, parameters (built in a form: string, number, integer, boolean, enum; required or
  optional; a description each), a method, a URL template, headers, a JSON body template, a timeout
  (1–30 s, default 8), an optional waiting line and failure line, a **confirm first** flag, and an
  optional mock response. Templates use `{{param}}`, `{{secrets.NAME}}` and `{{variable}}`.
  (product FR-19)
- **FR-3.** The tool editor MUST offer **Try it**: run the tool with sample arguments and show the
  resolved request (secrets masked), the response status, headers, body (truncated to 64 KB) and
  latency. A response can be kept as the tool's sample, used for result mapping (FR-7) and mock
  (FR-10).
- **FR-4.** Users MUST be able to start a tool from a **gallery** of templates for services that
  use API keys or tokens. A template fills every field, names the secrets it needs and shows a
  short setup checklist. The first gallery has at least six templates (proposal in plan DD-6).
- **FR-5.** The Tools page SHOULD show, per tool, calls, failures and median latency over the last
  seven days, from stored session events.

### Agents using tools
- **FR-6.** Users MUST be able to attach workspace tools to an agent and narrow them per Agent step
  (product FR-23). The LLM sees each attached tool's name, description and parameter schema and
  may call it. Arguments are validated against the schema before the call; invalid arguments are
  returned to the LLM as an error once, so it can correct them.
- **FR-7.** The **Tool call** node MUST run a tool without the LLM choosing it: arguments come from
  expressions over variables, and a result map writes response fields (JSONPath) into variables.
  After the call the node sets `tool.ok` (boolean) and `tool.status` (HTTP status or `timeout` /
  `error`), so outgoing edges can route on success or failure with ordinary conditions.
- **FR-8.** For a **confirm first** tool, the engine MUST NOT execute an LLM-initiated call until the
  agent has read the arguments back to the caller and the caller has agreed in a later turn. A Tool
  call node never asks (the builder put it in the flow deliberately).
- **FR-9.** While a call runs, the agent MUST say the tool's waiting line if it has one. When a call
  fails or times out, the LLM receives the failure and the tool's failure line, so the agent can
  apologise and offer an alternative instead of inventing a result.
- **FR-10.** When a tool's mock is on, console sessions MUST use the mock response instead of calling
  the service, and mark the events as mock. Mock never applies to non-console channels.
- **FR-11.** The runtime MUST provide the built-in tools `go_to_node` (move to a named step) and
  `set_variable` (set a declared variable, type-checked), attachable like any tool.
  (product FR-22)
- **FR-12.** Publishing MUST snapshot the definitions of the tools a version uses (secrets stay
  references), and sessions on that version run the snapshot (ADR-0011). Editing or deleting a tool
  changes only the draft and later versions; a draft that uses a deleted tool shows a problem.

### Visibility and safety
- **FR-13.** The console MUST show each tool call with the tool name, arguments, mock or live,
  status, latency and the (truncated, masked) result, and the canvas MUST show the active step as
  calling that tool. Sessions store the same as events.
- **FR-14.** Tool calls MUST only use `http` or `https`, MUST NOT reach loopback, private,
  link-local or cloud-metadata addresses (checked after DNS resolution) unless the operator allows
  hosts in `OVAS_TOOL_ALLOWED_HOSTS`, MUST cap response bodies at 1 MB, and MUST stop after 30 tool
  calls in one session.

## 6. Non-functional requirements

- **NFR-1 Security.** Secrets are encrypted at rest with `OVAS_SECRET_KEY` (AES-GCM, as the LLM key)
  and only decrypted inside the process that makes the call. A test asserts that a known secret
  value never appears in any API response, log record or stored event.
- **NFR-2 Latency.** The platform adds at most 50 ms (p95) to a tool call on top of the service's own
  response time, measured in the test bench against a local endpoint.
- **NFR-3 Stability.** API coverage stays at or above 80%; every AC has an automated test; the
  end-to-end suite covers gallery → try it (against a local test server) → attach → console call.
- **NFR-4 Accessibility.** The tool editor, parameter builder and gallery meet WCAG 2.2 AA.

## 7. Data model & contracts

```ts
Secret { id, name, created_at, updated_at, last_used_at }          // value write-only

Tool {
  id, name, description, kind: "webhook",
  parameters: JSONSchema,                       // built by the form; object with properties
  method: "GET"|"POST"|"PUT"|"PATCH"|"DELETE",
  url: string, headers: Record<string,string>, body: string | null,   // templates
  timeout_ms: number, wait_message: string | null, failure_message: string | null,
  confirm: boolean,
  mock: { enabled: boolean, status: number, body: unknown } | null,
  sample: { status: number, body: unknown } | null,
  template: string | null,                      // gallery template it started from
}

AgentSpec.tools: ToolRef[]                      // existing: builtin | { kind: "workspace", tool_id }
ToolCallNode.data: { label, tool: ToolRef, args: Record<string, Expr>, result_map: Record<string, JSONPath> }
AgentVersion.tool_snapshot: Record<tool_id, Tool>   // copied at publish

// session events (additions)
| { type: "tool_call", call_id, tool, arguments, mock: boolean, node_id }
| { type: "tool_result", call_id, tool, ok: boolean, status: number | "timeout" | "error",
    latency_ms: number, result: unknown /* ≤ 2 KB, masked */ }
| { type: "tool_confirm", call_id, tool, arguments }   // awaiting the caller's yes

POST /v1/tools/{id}/try { arguments } → { request: MaskedRequest, status, headers, body, latency_ms }
```

## 8. Acceptance criteria

- **AC-1.** (FR-1) Saving secret `CRM_KEY` then reading secrets returns its name and never its
  value; a tool header `Bearer {{secrets.CRM_KEY}}` arrives resolved at a test server; the value
  appears in no response, log record or event.
- **AC-2.** (FR-2) A tool built in the form produces the expected JSON Schema; names are unique per
  workspace; another workspace cannot read it.
- **AC-3.** (FR-3) **Try it** against a test server shows the masked request and the response; the
  response can be kept as the sample.
- **AC-4.** (FR-4) Each gallery template creates a tool with no empty required field and lists the
  secrets it needs.
- **AC-5.** (FR-6) With a tool attached, a console turn where the stub LLM calls it sends the request
  with the LLM's arguments and feeds the response back; invalid arguments are returned once as an
  error; a step that narrows tools hides the others.
- **AC-6.** (FR-7) A Tool call node sends arguments from variables, writes mapped fields into
  variables, sets `tool.ok`, and a `tool.ok` edge and an `else` edge route success and failure.
- **AC-7.** (FR-8) A confirm-first tool is not called on the LLM's first request; it is called after
  a later caller turn agrees; it is never called if the caller declines.
- **AC-8.** (FR-9) A waiting line is emitted before the call; a timeout gives the LLM the failure and
  failure line, and no invented result.
- **AC-9.** (FR-10) With mock on, the console session gets the mock body and no request reaches the
  test server; events are marked mock.
- **AC-10.** (FR-11) `go_to_node` moves to the named step; `set_variable` rejects a wrong type.
- **AC-11.** (FR-12) After publishing v1 and editing the tool's URL, a v1 session calls the old URL
  and a draft session the new one; deleting the tool flags the draft.
- **AC-12.** (FR-13) The console shows tool name, arguments, status and latency; the canvas shows
  the step calling the tool; the session stores both events.
- **AC-13.** (FR-14) URLs resolving to 127.0.0.1, 10.0.0.0/8, 169.254.169.254 and `file:` are
  refused with a clear message unless allowed in `OVAS_TOOL_ALLOWED_HOSTS`; a 2 MB response is cut
  at 1 MB; the 31st call in a session is refused.

## 9. Open questions

- **OQ-1.** Confirm the first gallery list (plan DD-6). Owner: devdaviddr.
- **OQ-2.** Should mock also apply when a published version is tested in the console? Proposed: yes,
  mock is a console switch per tool, whatever the target. Owner: devdaviddr.

## Changelog

| Version | Date | Level | Note |
| --- | --- | --- | --- |
| 0.1.0 | 2026-11-28 | init | Initial draft: secrets, webhook tools, gallery, try it, mock, Tool call node, confirm first, built-ins, snapshots, safety |
