---
feature: builder-assistant
title: "Builder assistant: build an agent by chatting"
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-28
updated: 2026-11-28
---

# Builder assistant — Specification

> **Stage 1 · SPECIFY.** New in product spec 1.1.0 (FR-36). Architecture in ADR-0021.

## 1. Problem & context

Building an agent on the canvas is clear once you know the node types, conditions and variables,
but a new user facing an empty canvas has to learn all of that before getting anything useful.
Most people can describe what they want ("answer questions about our clinic, book cleanings, take
a message for anything else") much faster than they can draw it.

Experienced builders have the opposite problem: small, repetitive edits ("also collect their
email", "add a cancellation path") take many clicks.

## 2. Goals

- A new user who describes their agent and answers a few questions gets a valid, sensible first
  version on the canvas in under five minutes, without touching the palette.
- An experienced builder can ask for a change in plain language and review exactly what will
  change before it does.
- The assistant never leaves the draft broken and never changes it without the user's say-so.
- It works with the workspace's own LLM, including local models such as Strata or qwen3.5:9b.

## 3. Non-goals

- Publishing, rolling back or deleting agents: the assistant only proposes draft edits.
- Entering secret values or calling real services: it may draft a webhook tool definition, but the
  user adds secrets and presses Try it.
- Simulated test callers ("test it for me"): planned for a later version.
- Building several agents at once, handoffs between agents.
- A voice-first assistant: push-to-talk works in its chat box, as in the console, but no more.

## 4. User scenarios

- As a **new user**, I choose **Describe it** when creating an agent, type "a receptionist for my
  physio clinic that books appointments and answers questions about prices", answer five short
  questions (with "you decide" available on each), approve a plan, and watch the flow appear.
- As a **builder**, I type "also ask for their email before booking"; the assistant shows the new
  Extract field and the changed step as ghosts on the canvas with a short change list; I press
  **Accept** and it becomes an ordinary draft edit I can undo.
- As a **builder**, I reject a proposal and say "no, put it after the date"; it proposes again.
- As a **teammate**, I ask "explain this flow" and get a plain walkthrough where each step name
  selects its node.

## 5. Functional requirements

- **FR-1.** The builder MUST offer an **Assistant** panel (next to Test) with a streaming chat, and
  the New agent dialog MUST offer **Describe it** next to the templates, which opens the builder
  with the assistant started on that description.
- **FR-2.** For a new or empty agent, the assistant MUST interview the user one question at a time
  (at most eight) about purpose, callers, what to collect, branches, endings and outcomes, tone and
  voice, documents and tools; each question offers quick replies including "you decide".
- **FR-3.** Before building, the assistant MUST show a plan (steps, variables, branches, documents
  and tools it will use or create) and wait for the user to confirm or change it.
- **FR-4.** Every change MUST arrive as a **proposal**: added, changed and removed nodes and edges
  shown on the canvas as ghosts, changed settings and variables in a change list, and **Accept** /
  **Reject**. Accepting applies the whole proposal as one draft edit (one undo step). Nothing
  changes until the user accepts.
- **FR-5.** The assistant MUST change agents only through a fixed set of graph operations (plan
  DD-1). Each proposal MUST pass `ovas_core` validation before it is shown; the assistant repairs
  validation errors itself (up to three attempts) and, if it cannot, shows the proposal with the
  remaining problems and says so.
- **FR-6.** The assistant MUST work from the current draft, including manual edits made since its
  last message, and from the workspace's documents and tools. If the draft changes while a
  proposal is open, the proposal MUST be marked out of date and offered again on the new draft.
- **FR-7.** Edit requests MUST produce the smallest proposal that does the job: unrelated nodes
  keep their ids, positions and content.
- **FR-8.** New nodes MUST be placed by an automatic left-to-right layout that does not overlap
  existing nodes; existing nodes do not move unless the user asks for a tidy-up.
- **FR-9.** "Explain this flow" (and similar questions) MUST answer in plain language, naming steps
  as links that select the node on the canvas.
- **FR-10.** The conversation MUST be kept per agent and per user, shown again when the panel
  reopens, and clearable.
- **FR-11.** The assistant MUST use the workspace LLM. It MUST NOT send secret values, API keys or
  stored session transcripts to the LLM; it may send the draft, variable names, document names and
  tool definitions (with secrets as references).

## 6. Non-functional requirements

- **NFR-1 Speed.** With Strata q2_0 or qwen3.5:9b, the first proposal for a six-step agent appears
  within 60 s of confirming the plan, and an edit proposal within 20 s (measured, median of five).
- **NFR-2 Reliability.** On a fixed set of 20 scripted briefs, at least 18 produce a valid proposal
  without user correction, with the default local model. The set lives in the repo and runs on
  demand (not in CI, which uses the stub LLM).
- **NFR-3 Security.** As FR-11; a test asserts no secret value appears in any LLM request.
- **NFR-4 Accessibility.** The panel and the proposal review are keyboard-operable and announce
  proposals to screen readers; ghosts are distinguishable without colour.

## 7. Data model & contracts

```ts
AssistantThread { id, agent_id, user_id, messages: AssistantMessage[], updated_at }
AssistantMessage = { role: "user" | "assistant", text, proposal_id?, quick_replies?: string[] }

Proposal {
  id, thread_id, base_revision: number,        // draft revision it was made against
  summary: string, ops: Op[], issues: Issue[],  // issues left after repair attempts
  status: "open" | "accepted" | "rejected" | "stale"
}

Op =
  | { op: "add_node", node: Node }                       // id chosen by the assistant, prefixed
  | { op: "update_node", id, data: Partial<NodeData> }
  | { op: "remove_node", id }
  | { op: "connect", edge: Edge }
  | { op: "update_edge", id, condition?, order? }
  | { op: "disconnect", id }
  | { op: "set_settings", settings: Partial<AgentSettings> }
  | { op: "upsert_variable", variable: VariableDef }
  | { op: "remove_variable", name }
  | { op: "attach_knowledge", source_id } | { op: "attach_tool", tool: ToolRef }
  | { op: "draft_tool", tool: Tool }                     // created only on accept; no secret values

// stream events (assistant channel)
| { type: "token", text } | { type: "quick_replies", options: string[] }
| { type: "plan", steps: string[], variables: string[], uses: string[] }
| { type: "proposal", proposal: Proposal } | { type: "error", message }
```

## 8. Acceptance criteria

- **AC-1.** (FR-1) **Describe it** creates an agent and opens the builder with the assistant
  started; the panel opens and closes from the toolbar.
- **AC-2.** (FR-2, FR-3) With the stub LLM, a new agent gets at most eight questions, each with a
  "you decide" reply, then a plan; nothing is proposed before the plan is confirmed.
- **AC-3.** (FR-4) A proposal shows ghosts and a change list; the draft revision is unchanged until
  Accept; Accept saves one revision and one undo restores the previous draft; Reject leaves it.
- **AC-4.** (FR-5) A proposal whose operations make an invalid graph is repaired before display;
  an unrepairable one is shown with its issues and a warning.
- **AC-5.** (FR-6) Editing the draft by hand while a proposal is open marks it stale and offers a
  fresh one based on the new revision.
- **AC-6.** (FR-7) "Also collect their email" on the receptionist template changes only the
  relevant Extract node and variables; every other node keeps its id, position and data.
- **AC-7.** (FR-8) Added nodes never overlap existing ones; existing positions are unchanged.
- **AC-8.** (FR-9) "Explain this flow" names every reachable step, and each name selects its node.
- **AC-9.** (FR-10) Reopening the builder shows the previous conversation; Clear empties it.
- **AC-10.** (FR-11, NFR-3) With a secret `CRM_KEY` and a tool using it, no LLM request made by the
  assistant contains the secret's value.

## 9. Open questions

- **OQ-1.** Should accepted proposals be attributed in the version history (for example "via
  assistant")? Proposed: yes, as a note on the draft revision. Owner: devdaviddr.
- **OQ-2.** Default for "you decide": the assistant's choice, or the receptionist template's
  pattern? Proposed: the assistant's choice, stated in the plan. Owner: devdaviddr.

## Changelog

| Version | Date | Level | Note |
| --- | --- | --- | --- |
| 0.1.0 | 2026-11-28 | init | Initial draft: interview, plan, proposals as validated operations, edits, explain |
