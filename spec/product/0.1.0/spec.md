---
feature: product
title: Open Voice Agent Studio v1
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-27
updated: 2026-11-27
---

# Open Voice Agent Studio v1 — Specification

> **Stage 1 · SPECIFY.** This is the product-level contract for v1.0.0. Each milestone (M0–M5) gets
> its own spec under `spec/<milestone>/` that refines the requirements here into buildable detail.
> The *how* lives in `plan.md`; the milestone order lives in `tasks.md`.

## 1. Problem & context

Teams that want a voice agent today choose between hosted platforms (ElevenLabs Agents, Vapi,
Retell) and frameworks (Pipecat, LiveKit Agents). The platforms give a visual builder, versioning,
tools and analytics, but they are closed, priced per minute, and send every call to someone else's
cloud. The frameworks are open and self-hostable, but every team rebuilds the same studio on top:
the builder, the versioning, the tool wiring, the test console, the transcripts.

Open Voice Agent Studio (code name `ovas`) is that studio, open source (MIT) and self-hosted. People
design a voice agent as a conversation workflow on a visual canvas, give it tools, memory and
knowledge, test it by talking to it, publish immutable versions, and embed it in a website. It runs
fully offline on local models by default, and uses cloud providers only when the operator adds keys.

## 2. Goals

- A developer can go from `docker compose up` to talking with their first agent in under 15 minutes,
  with no API keys.
- Agents are designed as conversation workflows (steps, conditions, tools) on a React Flow canvas,
  not as one giant prompt.
- Every change is versioned. What answered a given conversation can always be traced to an
  immutable version, and rollback takes one action.
- Everything the studio can do is available through a public REST API and a CLI, so agents can live
  in git.
- Every model provider (speech-to-text, text-to-speech, LLM, embeddings) is swappable, and a fully
  local stack is the default.

## 3. Non-goals (v1)

- Phone calls (Twilio, SIP) and human transfer. Planned for v2.
- A/B traffic splits between versions, and git-style branches. Planned for v2.
- Automated scenario evaluations. Planned for v1.1.
- Custom node types as plugins. Planned for v2; providers are pluggable in v1.
- Hosted multi-tenant operation (billing, quotas, org admin). The schema allows it; v1 ships one
  workspace per install.
- Voice cloning or training.
- Languages other than English as a tested, supported path (the schema carries `language`).

## 4. User scenarios

- As an **agent builder**, I want to drag conversation steps onto a canvas and connect them with
  conditions, so that a booking agent follows a reliable path instead of improvising.
- As an **agent builder**, I want to talk to my draft in a test console and watch which node is
  active, which tools ran and how long each turn took, so that I can debug by ear and by eye.
- As an **agent builder**, I want to publish a version with a message and roll back if it misbehaves,
  so that I can change a live agent safely.
- As a **developer**, I want to give an agent an HTTP tool or an MCP server, so that it can look up
  orders or book slots in my systems.
- As a **developer**, I want to export an agent as YAML and push it from CI, so that agent changes
  are reviewed in pull requests like code.
- As a **site owner**, I want to paste one script tag to put a themed voice widget on my site, so
  that visitors can talk to the agent.
- As an **operator**, I want the whole stack to run on my own hardware with local models, so that no
  audio or transcript leaves my network.
- As an **end user** of an agent, I want to see and delete what the agent remembers about me.

## 5. Functional requirements

### Workspace and access
- **FR-1.** The system MUST support local user accounts with email and password sign-in.
- **FR-2.** Every stored entity MUST belong to a workspace. Users have a role per workspace
  (`owner` or `member` enforced in v1).
- **FR-3.** Owners MUST be able to create and revoke workspace API keys for programmatic access.

### Agents and the builder
- **FR-4.** Users MUST be able to create, rename, duplicate and delete agents. Each agent has exactly
  one editable draft.
- **FR-5.** The builder MUST let users edit an agent's workflow graph on a canvas, using the v1 node
  catalogue: Start, Agent step, Extract, Router, Tool call, Handoff, End, Note.
- **FR-6.** Edges out of Agent step and Router nodes MUST support three condition kinds: an
  LLM-judged natural-language condition, a CEL expression over session variables, and an `else`
  fallback. Edges are evaluated in their stored order, expressions before LLM-judged conditions.
- **FR-7.** The system MUST validate a graph and show every problem on the canvas: exactly one Start
  node, every node reachable from Start, every path able to reach an End or Handoff, valid CEL,
  references to existing tools, variables, knowledge sources and agents.
- **FR-8.** Agents MUST have settings (prompt, first message, language, voice, speed, LLM,
  temperature, turn-taking sensitivity, interruptions on/off, max session length, idle timeout), and
  Agent step nodes MUST be able to override any of them.
- **FR-9.** Agents MUST support a pronunciation dictionary applied to text before speech synthesis.

### Versioning
- **FR-10.** Publishing MUST freeze the draft into an immutable, sequentially numbered version with a
  message, author, timestamp and a complete snapshot of graph, settings and attached resources.
- **FR-11.** Each agent MUST have a `live` pointer and MAY have further named environments (for
  example `staging`), each pointing at one version. Rollback MUST be a pointer move.
- **FR-12.** The system MUST show a diff between any two versions, or a version and the draft, at the
  level of nodes, edges, settings and prompt text.
- **FR-13.** Every session MUST record the agent version (or draft revision) it ran.

### Runtime
- **FR-14.** The runtime MUST run a real-time voice session over WebRTC from a browser, executing a
  version's workflow: speech-to-text, LLM, tools and text-to-speech, moving between nodes as edges
  fire.
- **FR-15.** Sessions MUST support voice activity detection, end-of-turn detection and user
  interruption (barge-in), configurable per agent.
- **FR-16.** The same agent MUST be runnable in text mode (typed input, text output, same workflow
  and tools).
- **FR-17.** Speech-to-text, text-to-speech, LLM and embedding providers MUST sit behind a provider
  interface, and third parties MUST be able to add providers as installable plugins without
  modifying the repo.
- **FR-18.** A default install MUST run end to end with no external network access and no API keys,
  using bundled local providers.
- **FR-35.** Agents and nodes MUST carry a `language` field passed to providers.

### Tools
- **FR-19.** Users MUST be able to define HTTP webhook tools: name, description, JSON Schema
  parameters, URL, method, headers, timeout, and secret references.
- **FR-20.** Users MUST be able to connect MCP servers to a workspace and expose their tools to
  agents.
- **FR-21.** Agents MUST support client tools, which are delivered as events to the embedding page
  and whose results return to the session.
- **FR-22.** The runtime MUST provide built-in tools: end session, go to node, set variable.
- **FR-23.** Tools MUST be attachable per agent and narrowable per Agent step node.
- **FR-24.** Secrets MUST be stored encrypted at rest, MUST be writable but never readable through
  the API, MUST never appear in logs, and MUST be referenced as `{{secrets.NAME}}` and resolved only
  server-side.

### Context, memory and knowledge
- **FR-25.** Sessions MUST have a typed variable store, seeded at start by the caller (API or
  widget), written by Extract nodes, tool mappings and built-ins, and usable in prompts as
  `{{variable}}`.
- **FR-26.** Conversation history MUST be kept within a per-agent token budget by summarising or
  trimming older turns.
- **FR-27.** Agents MAY enable long-term memory (off by default): facts are extracted per end user
  after each session, recalled at session start and through a `recall_memory` tool, and can be
  listed and deleted per end user through the API.
- **FR-28.** Workspaces MUST support a knowledge base: upload PDF, Markdown, text or DOCX, or crawl a
  URL; content is chunked and embedded; sources attach to agents and narrow per node; retrieval is
  through a `search_knowledge` tool, with optional automatic top-k injection per node.

### Channels
- **FR-29.** The studio MUST include a test console that runs the draft or any version in voice or
  text mode and shows the live transcript, active node, tool calls, variable changes and per-turn
  latency.
- **FR-30.** The system MUST provide an embeddable web widget, configured per agent with a public
  key, an allowed-origins list and theme settings (colours, avatar or orb style, position, labels,
  light/dark).

### Observability and data
- **FR-31.** Each session MUST store its transcript, an ordered event timeline (node changes, tool
  calls with inputs and outputs, variable changes), per-turn latency for STT, LLM and TTS, token
  usage, and its version. Audio recording MUST be opt-in per agent.
- **FR-32.** The runtime and API MUST be able to export OpenTelemetry traces to a configured
  collector.
- **FR-33.** Workspaces MUST have retention settings (recordings default 30 days; transcripts kept
  until deleted). Deleting a session MUST delete its transcript, events, recording, and memories
  extracted from it.

### Agents as code
- **FR-34.** Every studio capability MUST be available through a documented REST API (OpenAPI), and
  a CLI MUST export and import agents as YAML (`pull`, `push`, `publish`, `diff`).

## 6. Non-functional requirements

- **NFR-1 Latency.** Voice-to-voice response time (user stops speaking → first agent audio), p50, on
  the reference hardware with local providers: **[NEEDS INPUT: target and reference hardware, see
  OQ-1]**. Each turn's latency breakdown is measured and stored (FR-31) so the target is testable.
- **NFR-2 Install.** `docker compose up` on a machine with 16 GB RAM and no GPU MUST reach a working
  voice session with the default local stack. A GPU, when present, is used automatically.
- **NFR-3 Security.** Secrets per FR-24; passwords hashed with argon2id; session cookies HTTP-only,
  Secure, SameSite=Lax; widget keys only start sessions for their agent from allowed origins;
  webhook tools cannot reach link-local or metadata addresses unless an operator allows it.
- **NFR-4 Privacy.** No telemetry leaves the install unless the operator configures it. End-user
  memory can be listed and deleted (FR-27).
- **NFR-5 Accessibility.** The studio meets WCAG 2.2 AA for the non-canvas UI, and every canvas
  action has a keyboard path.
- **NFR-6 Openness.** MIT license. No feature requires a proprietary service.
- **NFR-7 Quality.** Every FR has an acceptance test. Lint, typecheck, tests and schema-codegen
  drift checks run locally (hooks) and on every pull request.
- **NFR-8 Compatibility.** The REST API and the graph schema are versioned; a published agent
  version keeps running after an upgrade (schema migrations upgrade snapshots or the runtime reads
  older schema versions).

## 7. Data model & contracts

Shapes are normative; field names may gain additions (minor bump) but not change (major bump).
Every entity also has `id` (UUIDv7), `workspace_id`, `created_at`, `updated_at`.

```ts
Workspace   { name, retention: { recordings_days: number|null, transcripts_days: number|null } }
User        { email, display_name }
Membership  { user_id, role: "owner" | "member" }
ApiKey      { name, prefix, last_used_at }            // secret shown once at creation

Agent {
  name, description,
  draft: AgentSpec, draft_revision: number,
  environments: Record<string, version_number>        // always has "live" once published
}
AgentVersion { agent_id, number, message, author_id, spec: AgentSpec, schema_version: string }

AgentSpec {
  schema_version: "1",
  settings: AgentSettings,
  graph: { nodes: Node[], edges: Edge[] },
  tools: ToolRef[], knowledge: KnowledgeRef[],
  variables: VariableDef[],                           // declared, typed
  pronunciation: { term: string, say: string }[],
  memory: { enabled: boolean },
  recording: { enabled: boolean }
}
AgentSettings {
  prompt, first_message, language,
  voice: { provider, voice_id, speed },
  llm:   { provider, model, temperature },
  stt:   { provider, model },
  turn:  { sensitivity: "low"|"medium"|"high", interruptions: boolean },
  limits:{ max_session_seconds, idle_timeout_seconds },
  history_token_budget
}
Node =
  | { type: "start",      id, position, data: { first_message?, set?: Record<string, Expr> } }
  | { type: "agent_step", id, position, data: { label, prompt, overrides?: Partial<AgentSettings>,
                                               tools?: ToolRef[], knowledge?: KnowledgeRef[],
                                               auto_knowledge_top_k?: number } }
  | { type: "extract",    id, position, data: { label, instructions, outputs: VariableDef[] } }
  | { type: "router",     id, position, data: { label } }
  | { type: "tool_call",  id, position, data: { tool: ToolRef, args: Record<string, Expr>,
                                               result_map: Record<string, string> } }
  | { type: "handoff",    id, position, data: { agent_id, environment: string, pass_variables: string[] } }
  | { type: "end",        id, position, data: { message?, outcome: string } }
  | { type: "note",       id, position, data: { text } }
Edge { id, source, target, order: number,
       condition: { kind: "llm", text } | { kind: "cel", expr } | { kind: "else" } }
VariableDef { name, type: "string"|"number"|"boolean"|"date"|"email"|"enum"|"object", enum?, description }

Tool =
  | { kind: "webhook", name, description, parameters: JSONSchema, url, method,
      headers: Record<string,string>, timeout_ms }    // values may contain {{secrets.NAME}}
  | { kind: "mcp", server_id, tool_name }             // discovered from McpServer
  | { kind: "client", name, description, parameters: JSONSchema, timeout_ms }
McpServer   { name, transport: "streamable_http"|"stdio", url?, command?, headers }
Secret      { name }                                  // value write-only

KnowledgeSource { name, kind: "file"|"url", status: "pending"|"indexing"|"ready"|"failed", chunks: number }
Memory      { agent_id, end_user_id, fact, source_session_id, embedding }

Session {
  agent_id, version_number | null, draft_revision | null, mode: "voice"|"text",
  channel: "console"|"widget"|"api", end_user_id?, started_at, ended_at, outcome?,
  variables: Record<string, unknown>, usage: { llm_tokens_in, llm_tokens_out, tts_chars, stt_seconds }
}
SessionEvent { session_id, seq, at, type: "turn"|"node_enter"|"edge"|"tool_call"|"tool_result"
               |"variable_set"|"interruption"|"error", payload, latency?: { stt_ms, llm_ttft_ms, tts_ttfb_ms } }

Widget { agent_id, environment, public_key, allowed_origins: string[], theme: WidgetTheme }
```

## 8. Acceptance criteria

- **AC-1.** (FR-1) Given a new install, when a user signs up and signs in, then they reach the
  agent list; a wrong password is rejected.
- **AC-2.** (FR-2) Given two workspaces in the database, when a member of one lists agents, then
  only that workspace's agents are returned (row-level test across every entity).
- **AC-3.** (FR-3) Given an owner creates an API key, when it is used as a bearer token, then the API
  accepts it; after revocation it returns 401.
- **AC-4.** (FR-4) Given an agent, when it is duplicated, then the copy has an identical draft and no
  versions.
- **AC-5.** (FR-5) Given the builder, when a user adds one node of each catalogue type and saves,
  then reloading shows the same graph.
- **AC-6.** (FR-6) Given a Router with edges `cel: x > 5`, `llm: "user is angry"`, `else`, when
  `x = 7`, then the CEL edge fires without an LLM call.
- **AC-7.** (FR-7) Given a graph with an unreachable node and invalid CEL, when it is validated, then
  both problems are reported against their node/edge IDs and publish is blocked.
- **AC-8.** (FR-8) Given an agent voice `af_heart` and a node override `am_adam`, when the session
  enters that node, then TTS uses `am_adam`.
- **AC-9.** (FR-9) Given a pronunciation entry `ovas → oh-vass`, when the agent says "ovas", then the
  TTS input contains "oh-vass".
- **AC-10.** (FR-10) Given a published v1, when the draft is edited, then v1's stored spec is
  unchanged and any attempt to update it is rejected.
- **AC-11.** (FR-11) Given `live → v2`, when the user rolls back to v1, then new sessions run v1 and
  existing sessions keep v2.
- **AC-12.** (FR-12) Given v1 and v2 differ by one node prompt and one edge, then the diff lists
  exactly those changes.
- **AC-13.** (FR-13) Given any finished session, then it records a version number or draft revision.
- **AC-14.** (FR-14) Given a published agent with Start → Agent step → End, when a browser connects
  and speaks, then it hears the first message and a reply, and reaching End closes the session.
- **AC-15.** (FR-15) Given the agent is speaking, when the user starts talking, then agent audio
  stops within the measured interruption latency and an `interruption` event is stored.
- **AC-16.** (FR-16) Given the AC-14 agent, when run in text mode, then the same node path is taken.
- **AC-17.** (FR-17) Given an external package that registers a TTS provider through the plugin
  entry point, when it is installed, then the provider appears in voice settings and can speak.
- **AC-18.** (FR-18) Given the default compose stack with outbound network blocked (after model
  download), then AC-14 passes.
- **AC-19.** (FR-19) Given a webhook tool against a test server, when the LLM calls it, then the
  server receives schema-valid arguments and the result reaches the LLM.
- **AC-20.** (FR-20) Given a connected MCP test server with two tools, then both appear for
  attachment and a call succeeds.
- **AC-21.** (FR-21) Given a client tool, when the agent calls it, then the widget host page receives
  the event and its returned value reaches the session.
- **AC-22.** (FR-22) Given the built-in `go_to_node`, when the LLM calls it with a valid node ID, then
  the session moves to that node.
- **AC-23.** (FR-23) Given an agent with tools A and B and a node narrowed to A, then the LLM at that
  node is offered only A.
- **AC-24.** (FR-24) Given a secret `CRM_KEY`, then no API response, log line or session event
  contains its value, and a webhook header `{{secrets.CRM_KEY}}` arrives resolved at the test server.
- **AC-25.** (FR-25) Given a session started with `{name: "Ana"}`, then a prompt `Hi {{name}}`
  renders "Hi Ana", and an Extract node's outputs appear in the variable store.
- **AC-26.** (FR-26) Given a long conversation, then the LLM input never exceeds the configured
  history budget.
- **AC-27.** (FR-27) Given memory enabled and an end user who said their dog is called Rex, then the
  next session for that end user recalls it; after deletion through the API it does not.
- **AC-28.** (FR-28) Given an uploaded Markdown file, when it is ready and the agent calls
  `search_knowledge`, then a matching chunk is returned with its source.
- **AC-29.** (FR-29) Given the console running a draft, then the UI shows each turn, the active node,
  tool calls and per-turn latency as they happen.
- **AC-30.** (FR-30) Given a widget with allowed origin `https://a.test`, then a session from
  `https://a.test` starts and one from `https://b.test` is refused.
- **AC-31.** (FR-31) Given a finished voice session, then its transcript, events, latency per turn,
  usage and version are retrievable; with recording off, no audio is stored.
- **AC-32.** (FR-32) Given an OTLP endpoint configured, then a session produces a trace with spans
  for STT, LLM, TTS and tool calls.
- **AC-33.** (FR-33) Given a session with extracted memories, when it is deleted, then its
  transcript, events, recording and those memories are gone.
- **AC-34.** (FR-34) Given an agent, when `ovas pull` then `ovas push` to a fresh workspace, then the
  draft is identical; every studio action has a documented endpoint.
- **AC-35.** (FR-35) Given an agent with `language: "es"`, then STT and TTS receive `es`.

## 9. Open questions

- **OQ-1.** NFR-1 latency target and reference hardware. Proposal: p50 ≤ 1.5 s on a CPU-only
  16 GB machine and ≤ 800 ms with a consumer GPU, measured on the AC-14 agent. Owner: devdaviddr.
  Must be settled before the M2 spec is approved.
- **OQ-2.** Concurrency target for one runtime process (sessions in parallel). Proposal: measured in
  M2 and set then. Owner: devdaviddr. Deferred to M2.

## Changelog

| Version | Date | Level | Note |
| --- | --- | --- | --- |
| 0.1.0 | 2026-11-27 | init | Initial draft from design grilling (35 decisions) |
