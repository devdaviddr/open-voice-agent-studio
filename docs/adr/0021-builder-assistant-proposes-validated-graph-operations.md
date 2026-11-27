# ADR-0021: Builder assistant proposes validated graph operations

- **Status:** Proposed
- **Date:** 2026-11-28

## Context

Users should be able to build and change an agent by chatting (product FR-36,
`spec/builder-assistant`). The assistant must work with small local models, must never leave the
draft broken, and must never change it without the user's agreement. Drafts already have autosave,
revisions with conflict detection, undo and validation (ADR-0011, MVP FR-7, FR-8).

## Decision

The assistant changes an agent only through a fixed set of **graph operations** (add, update or
remove a node; connect, update or disconnect an edge; set settings; upsert or remove a variable;
attach knowledge or a tool; draft a tool). Each LLM turn returns structured output with optional
operations. Pure code in `ovas-core` applies them to a copy of the draft, lays out new nodes
without moving existing ones, and validates the result; validation issues go back to the LLM for
up to three repairs. The result is stored as a **proposal** (operations, resulting spec, remaining
issues, base revision) and shown in the studio as ghosts. Accepting saves it through the normal
draft API as one revision and one undo step; a revision conflict marks it stale. The conversation
loop runs in the runtime; threads and proposals are stored by the API.

## Consequences

Small models only need to produce short, local operations instead of whole specs, and every
proposal is checked by the same validator as manual edits. Undo, conflicts, versions and diff need
no special cases. The operation set becomes a contract that must grow with the schema (for example
when Handoff nodes arrive). Proposals cost one validation pass per repair, which is cheap.

## Alternatives considered

- **Regenerate the whole `AgentSpec` each turn:** simple, but small models get large JSON wrong
  and every edit rewrites everything, losing positions and ids.
- **Apply changes directly, undo if unwanted:** faster, but changes the draft without consent and
  races with autosave.
- **Build the assistant as an OVAS agent on the existing engine:** attractive dog-fooding, but the
  engine is shaped for spoken turns and step routing rather than long structured tool loops.
  Revisit when the engine has a text-first mode.
