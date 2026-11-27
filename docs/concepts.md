# Concepts

## Workspace

Everything belongs to a workspace: agents, documents, sessions and the LLM settings. The first
user is its **owner** and can change workspace settings; later users are **members**.

## Agent

An agent is a conversation **workflow**: a graph of nodes joined by edges, plus settings that apply
everywhere (prompt, first message, model, temperature, voice, history budget, memory, knowledge).
Its definition is one JSON document, the `AgentSpec`, defined in `packages/core`.

## Nodes

| Node | What it does |
| --- | --- |
| **Start** | Where every conversation begins. Says the first message. |
| **Agent step** | A stretch of conversation with its own prompt. It can override the model, temperature and voice, narrow which documents and tools it uses, and add the best document passages to every turn. |
| **Extract** | Reads the conversation and fills variables, checking their types. Silent. |
| **Router** | Chooses where to go next from conditions alone. Silent. |
| **End** | Says goodbye and tags the session with an outcome, such as `booked`. |
| **Note** | A comment on the canvas. Ignored when the agent runs. |

## Edges and conditions

After each reply the engine checks the current node's outgoing edges, in their **order**:

- an **expression** (CEL), for example `caller.age >= 18`, evaluated against the variables;
- a **natural-language condition**, for example "the caller wants to book", judged by the LLM
  (all such conditions on a node are judged in one call);
- **else**, taken when nothing else fires. A Router must have one.

An edge without a condition always fires.

## Variables

Typed values the conversation collects: `string`, `number`, `boolean`, `date`, `email`, `enum` and
`object`, with dotted names such as `caller.name`. Use them in prompts as `{{caller.name}}`. Extract
nodes fill them; a value of the wrong type is rejected and the agent asks again.

## Draft, versions and live

You always edit the **draft**; it saves itself and detects edits from another tab. **Publish**
freezes it into an immutable, numbered **version** and points **live** at it. Versions can be
compared with each other or with the draft, restored into the draft, and made live again (rollback).

## Sessions

A session is one conversation, stored with its transcript, its events (steps entered, edges fired,
variables set, lookups) and the exact version or draft revision it ran. In the console a session can
have a **test caller ID**, which stands in for a real caller's identity.

## Knowledge

Documents uploaded to the workspace (Markdown, text, PDF, up to 20 MB). Each is split into
passages under its headings and embedded locally. An agent searches only the documents attached to
it, with the `search_knowledge` tool; an Agent step can narrow them and can add the top passages to
every turn automatically. A document a published version uses cannot be deleted.

## Memory

With memory on, when a session for a known caller ends, the LLM picks out lasting facts ("Their dog
is called Rex.") and they are stored for that agent and caller. The next session starts with the
five most recent; the `recall_memory` tool searches the rest. Facts can be deleted one by one, or a
caller forgotten entirely.

## Voice in the console

Replies can be read aloud with Kokoro, in the agent's or step's voice. **Push-to-talk** records a
clip in the browser, transcribes it with Whisper and sends the text as the caller's turn.
Real-time, interruptible voice for callers is planned (product milestone M2).
