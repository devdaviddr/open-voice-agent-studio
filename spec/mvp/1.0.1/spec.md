---
feature: mvp
title: "MVP: builder, auth, context and text test console"
version: 1.0.1
status: implemented
owner: devdaviddr
created: 2026-11-27
updated: 2026-11-28
---
# MVP — Specification

> **Stage 1 · SPECIFY.** The first usable release (app version 0.3.0). It cuts across the product
> milestones: the M0 foundations it stands on, most of M1 (builder, auth, versions), the text half
> of M2 plus push-to-talk voice input in the console, and M4 (knowledge, memory). Real-time voice
> (M2), tools (M3) and the widget (M5) are out.
> Requirements reference `spec/product/1.0.0/spec.md` where they implement a product FR.

## 1. Problem & context

The prototype on branch `prototype/builder` showed the builder layout, but nothing persists,
nobody signs in, and the agent cannot be run. The MVP makes the builder real: people sign in, build
an agent as a workflow, give it context (variables, documents, memory), publish versions, and talk
to it by text in a test console backed by a real LLM, with the replies optionally read aloud by
Kokoro.

## 2. Goals

- A new user can sign up, build the sample receptionist agent from a template, publish it and hold
  a text conversation with it in under 10 minutes.
- Nothing a user builds is lost: drafts autosave, and conflicting edits are detected, not
  overwritten.
- The agent's context is visible and controllable: variables, knowledge sources and memories are
  each listed, editable and traceable in the console.
- The repo is ready for AI agents to keep building it: CLAUDE.md, rules, docs and checks.

## 3. Non-goals (MVP)

- Real-time voice: WebRTC, voice activity detection, end-of-turn detection, barge-in (product M2).
  The console's push-to-talk (FR-23) is the only voice input in the MVP.
- Tool call and Handoff nodes, webhook and MCP tools, secrets vault UI beyond the LLM key (M3).
- Widget, public API keys, CLI, OpenTelemetry, retention settings (M5).
- Multiple workspaces per user, invitations, and password reset (no mail server in the MVP, and
  no admin command for it yet: a follow-up).
- Claude Code skills and hooks beyond the format-on-edit and guard hooks (rest stays in M0 spec).

## 4. User scenarios

- As a **new user**, I sign up with email and password and land on an empty agents page with a
  "Start from template" option.
- As a **builder**, I drag nodes from the palette, connect them, edit prompts and conditions in the
  inspector, and see validation problems on the canvas.
- As a **builder**, I declare variables such as `caller.name`, use them in prompts as
  `{{caller.name}}`, and add an Extract node that fills them.
- As a **builder**, I upload the clinic handbook and price list, attach them to the agent, and the
  agent answers price questions from them.
- As a **builder**, I switch on memory, talk to the agent as test caller "ana", end the chat, start a
  new one as "ana", and the agent remembers her dog is called Rex.
- As a **builder**, I publish v1, keep editing, compare the draft with v1, and roll `live` back.
- As a **builder**, I open the test console, chat with the draft, and watch the active node, edge
  decisions, variable changes and knowledge lookups as they happen.
- As a **builder**, I press the mic in the test console, say "I'd like to book a cleaning", and the
  agent replies to what I said, while the canvas shows it thinking, the edge it takes and the node
  it moves to.

## 5. Functional requirements

### Auth and workspace
- **FR-1.** Users MUST be able to sign up with email and password (min 10 characters), sign in and
  sign out. Passwords are hashed with argon2id. Sessions are server-side, referenced by an
  HTTP-only, SameSite=Lax cookie, expire after 14 days idle, and are deleted on sign-out.
  (product FR-1)
- **FR-2.** The first user to sign up becomes owner of the install's workspace. Later sign-ups join
  as members, unless the owner disables open sign-up in settings. Every entity is scoped to the
  workspace. (product FR-2)
- **FR-3.** Sign-in MUST be rate-limited per email and per IP (5 failures per 15 minutes), and
  state-changing requests MUST be rejected unless they carry a JSON content type and an allowed
  `Origin`.

### Agents and builder
- **FR-4.** Users MUST be able to list, create (blank or from the receptionist template), rename,
  duplicate and delete agents. (product FR-4)
- **FR-5.** The builder MUST use layout A from the prototype: node palette left, canvas centre,
  inspector right, top bar with draft revision, live version, validation status, Test and Publish;
  plus a slide-out right panel with the test console and versions (layout C's panel).
- **FR-6.** MVP node catalogue: Start, Agent step, Extract, Router, End, Note. Edges carry LLM, CEL
  or else conditions with an order. (product FR-5, FR-6 minus Tool call and Handoff)
- **FR-7.** Drafts MUST autosave within 2 seconds of the last change. Each save sends the
  `draft_revision` it was based on; a stale revision returns 409 and the UI offers to reload or
  overwrite.
- **FR-8.** The builder MUST validate the draft on every change and before publish: one Start, all
  nodes reachable, every non-End node has an outgoing path, every Router has an `else` edge, CEL
  parses, `{{variables}}` used in prompts are declared, attached knowledge sources exist.
  Problems show on the node or edge and in a list; publish is blocked while any exist.
  (product FR-7)
- **FR-9.** Agent settings MUST include prompt, first message, language, LLM model, temperature,
  history token budget, voice and speed (for read-aloud), memory on/off; Agent step nodes can
  override prompt additions, model, temperature and voice. (product FR-8, subset)
- **FR-10.** The canvas MUST support undo/redo, delete, duplicate, copy/paste of nodes, fit view,
  and keyboard shortcuts for each, and remain usable at 50 nodes.

### Versions
- **FR-11.** Publish MUST freeze the draft into an immutable numbered version with a message and
  move `live` to it. Users can list versions, open a read-only view of any version, restore a
  version into the draft, and point `live` at any version. (product FR-10, FR-11)
- **FR-12.** The system MUST show a diff between the draft and any version, or two versions:
  nodes and edges added, removed or changed, and prompt text changes shown line by line.
  (product FR-12)

### Context
- **FR-13.** Agents MUST declare typed variables (string, number, boolean, date, email, enum).
  Prompts and first messages insert them with `{{name}}`. Extract nodes fill them from the
  conversation using the LLM with a JSON schema built from the declarations. Values are validated
  against their type before being stored. (product FR-25)
- **FR-14.** The engine MUST keep the conversation within the history token budget by summarising
  the oldest turns once the budget is exceeded. (product FR-26)
- **FR-15.** Users MUST be able to upload Markdown, text and PDF files (up to 20 MB each) to a
  workspace knowledge base, see indexing status, delete sources, and attach sources to an agent
  and narrow them per Agent step. Content is chunked and embedded locally. The agent retrieves
  through a `search_knowledge` tool, and an Agent step may enable automatic top-k injection.
  (product FR-28, file sources only)
- **FR-16.** Agents MAY enable long-term memory. When a session for an `end_user_id` ends, the
  system extracts durable facts and stores them with embeddings. New sessions for the same
  end user recall the top 5 relevant facts into the prompt, and a `recall_memory` tool searches
  them. Users can list and delete memories per agent and end user in the UI. (product FR-27)

### Test console
- **FR-17.** The console MUST run a text session against the draft or any version, with an
  optional test end-user ID, and stream the agent's reply token by token.
- **FR-18.** The console MUST show, live: the active node (also highlighted on the canvas), edge
  decisions with the condition that fired, variable changes, knowledge and memory lookups with
  results, and per-turn LLM latency (time to first token, total).
- **FR-19.** The console MAY read agent replies aloud through the Kokoro TTS service, using the
  agent's or node's voice.
- **FR-20.** Every console session MUST be stored with its transcript, events and the version or
  draft revision it ran, and be viewable later from a Sessions list. (product FR-13, FR-31 subset)
- **FR-21.** The workspace owner MUST be able to configure the LLM provider: an OpenAI-compatible
  base URL, a default model, and an API key stored encrypted and never returned. A "Test
  connection" button lists available models.
- **FR-23.** The console MUST offer push-to-talk voice input: the builder records a clip in the
  browser, a local Whisper speech-to-text provider (`providers/stt-whisper`, behind the API) turns
  it into text in the agent's language, and the text is sent as the caller's turn and shown as such.
  The clip is not stored. If the microphone or the provider is unavailable, the console says so and
  typing still works. (product FR-17 and FR-18 subset: a local, key-free STT provider)
- **FR-24.** While a console session runs, the canvas MUST animate what the agent is doing: the
  active node shows whether it is waiting for the caller, thinking (LLM call in flight), speaking
  (streaming or reading aloud) or running a tool or lookup; an edge animates when it fires; and the
  nodes and edges the session has passed through stay marked until the session is reset. Animations
  respect `prefers-reduced-motion`. (refines FR-18)

### Codebase context
- **FR-22.** The repo MUST carry the M0 foundations the MVP needs: the monorepo layout, Postgres
  with migrations, `ovas-core` schema with TS codegen and drift check, Makefile, CI, root and
  per-package CLAUDE.md, AGENTS.md, path-scoped rules, format-on-edit and guard hooks, README and
  docs (getting started, concepts, architecture). (M0 FR-1–FR-15, FR-17 partial, FR-18, FR-19)

## 6. Non-functional requirements

- **NFR-1 Stability.** API test coverage ≥ 80% lines; every AC below has an automated test; one
  Playwright end-to-end test walks sign-up → template → edit → publish → chat → memory recall.
- **NFR-2 Responsiveness.** Canvas interactions stay at 60 fps with 50 nodes on a 2020 laptop;
  autosave never blocks typing.
- **NFR-3 Security.** As FR-1, FR-3 and the LLM key in FR-21 (AES-GCM with `OVAS_SECRET_KEY`).
  No secret value appears in any API response, log or session event.
- **NFR-4 Offline.** With Ollama running on the host, the whole MVP works with no internet after
  the first model download.
- **NFR-5 Accessibility.** Non-canvas UI meets WCAG 2.2 AA; every canvas action has a keyboard path.

## 7. Data model & contracts

Follows `spec/product/1.0.0/spec.md` §7, restricted to the MVP node types. Additions:

```ts
Session { ... , mode: "text", channel: "console", end_user_id?: string }
UserSession { id, user_id, created_at, last_seen_at, expires_at }        // auth session
LlmProvider { base_url, default_model, api_key: Secret | null }          // one per workspace
KnowledgeSource { name, kind: "file", mime, bytes, status, chunks, error? }
KnowledgeChunk  { source_id, ordinal, text, embedding: vector(384) }
AgentSpec.knowledge: { source_id: string }[]                             // snapshotted into versions by id + content hash
```

Console wire protocol (WebSocket `wss://…/v1/sessions/{id}/stream`, JSON messages):

```ts
// client → server
{ type: "user_message", text: string } | { type: "end" }
// server → client
| { type: "node_enter", node_id: string }
| { type: "token", text: string }
| { type: "assistant_message", text: string, llm: { ttft_ms: number, total_ms: number } }
| { type: "edge", edge_id: string, from: string, to: string, condition: Condition }
| { type: "variable_set", name: string, value: unknown }
| { type: "knowledge", query: string, results: { source: string, text: string, score: number }[] }
| { type: "memory", recalled: { fact: string }[] } | { type: "memory_saved", facts: string[] }
| { type: "ended", outcome?: string } | { type: "error", message: string }
```

## 8. Acceptance criteria

- **AC-1.** (FR-1) Sign-up, sign-in and sign-out work; a wrong password is rejected; after sign-out
  the old cookie gets 401; a password under 10 characters is rejected.
- **AC-2.** (FR-2) The first user is owner; the second is member; with open sign-up off, a third
  sign-up is refused. A member of workspace A cannot read workspace B's agents (DB-level test).
- **AC-3.** (FR-3) The sixth failed sign-in within 15 minutes returns 429; a POST with a foreign
  `Origin` returns 403.
- **AC-4.** (FR-4) Create from template yields the receptionist graph; duplicate copies the draft
  with no versions; delete removes the agent and its sessions.
- **AC-5.** (FR-5, FR-6) Each MVP node type can be added from the palette, edited in the inspector
  and connected; reloading shows the same graph.
- **AC-6.** (FR-7) Two tabs edit the same draft; the second save gets 409 and the conflict dialog.
- **AC-7.** (FR-8) A graph with an unreachable node, a Router without `else`, bad CEL and an
  undeclared `{{x}}` shows four problems and Publish is disabled.
- **AC-8.** (FR-9) A node with a model override runs with that model (asserted on the LLM request).
- **AC-9.** (FR-10) Undo restores a deleted node with its edges; copy/paste duplicates a node with a
  new ID.
- **AC-10.** (FR-11) After publishing v1 and editing the draft, v1 is unchanged; pointing `live`
  back to v1 makes new sessions run v1.
- **AC-11.** (FR-12) Changing one prompt and removing one edge shows exactly those two changes.
- **AC-12.** (FR-13) A session seeded with `{caller: {name: "Ana"}}` renders `Hi {{caller.name}}`
  as "Hi Ana"; an Extract node fills `preferred_date` with a valid date and rejects an invalid one.
- **AC-13.** (FR-14) A 60-turn scripted conversation never sends more than the budget to the LLM,
  and a summary message appears once the budget is passed.
- **AC-14.** (FR-15) An uploaded Markdown file reaches `ready`; asking a question answered only by
  it triggers `search_knowledge` and the reply contains the answer.
- **AC-15.** (FR-16) With memory on, end user "ana" says her dog is Rex; a new session for "ana"
  recalls it; after deleting that memory in the UI, a new session does not.
- **AC-16.** (FR-17, FR-18) A console turn streams tokens and emits `node_enter`, `edge` and
  `variable_set` events, and the canvas highlights the active node.
- **AC-17.** (FR-19) With read-aloud on, each assistant message is fetched as audio from the TTS
  service with the node's voice.
- **AC-18.** (FR-20) A finished console session appears in Sessions with transcript, events and
  its version or draft revision.
- **AC-19.** (FR-21) Saving the LLM key then reading settings returns `api_key: {set: true}` and
  never the value; "Test connection" lists models from the configured endpoint.
- **AC-20.** (FR-22) `make check` passes in CI; codegen drift fails it; root CLAUDE.md, AGENTS.md,
  rules and docs exist; the format-on-edit and guard hooks pass their hook tests.
- **AC-21.** (FR-23) Posting a short WAV of "hello" to `/v1/stt` returns text containing "hello";
  without sign-in it returns 401; with the provider down it returns 502 with a readable message.
  In the console, a recorded clip's transcript appears as a caller message and the agent replies.
- **AC-22.** (FR-24) Given a session, sending a message puts the active node in `thinking`, the
  first token moves it to `speaking`, an `edge` event animates that edge and marks it visited, a
  `tool_call` shows `tool`, and ending or resetting the session clears all activity state.

## 9. Open questions

- None blocking. Product OQ-1 (voice latency target) does not apply to text mode or to
  push-to-talk, which is not real-time.

## Changelog

| Version | Date | Level | Note |
| --- | --- | --- | --- |
| 1.0.1 | 2026-11-28 | patch | Implemented: released as 0.3.0. Password reset by admin command was never built; moved to non-goals |
| 1.0.0 | 2026-11-28 | major | Approved by the maintainer (2026-11-28) |
| 0.2.1 | 2026-11-28 | patch | Reconcile knowledge with what was built: attachments live in AgentSpec.knowledge; versions pin sources by ID (content is immutable) |
| 0.2.0 | 2026-11-28 | minor | Add push-to-talk voice input (Whisper) and canvas activity animation to the test console |
| 0.1.0 | 2026-11-27 | init | Initial draft |