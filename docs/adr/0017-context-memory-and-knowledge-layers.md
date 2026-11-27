# ADR-0017: Context, memory and knowledge layers

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

"Memory" means different things: what the agent knows about this conversation, about this caller across conversations, and about the business.

## Decision

Four separately controlled layers: (1) a typed **session variable** store, seeded by the caller and written by Extract nodes, tool result mappings and built-ins, usable in prompts as `{{name}}`; (2) **conversation history** within a token budget, older turns summarised or trimmed; (3) opt-in **long-term memory** per end user, facts extracted after each session, recalled at start and through `recall_memory`, listable and deletable per end user; (4) a **knowledge base** of uploaded files and crawled URLs, chunked and embedded locally, attached per agent and node, retrieved through `search_knowledge` with optional automatic top-k injection.

## Consequences

Each layer has clear privacy and latency costs that users can switch on deliberately. Memory is off by default.

## Alternatives considered

One undifferentiated memory store (unclear privacy, unpredictable prompts).
