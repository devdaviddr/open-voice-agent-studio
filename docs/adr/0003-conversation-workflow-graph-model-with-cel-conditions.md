# ADR-0003: Conversation-workflow graph model with CEL conditions

- **Status:** Accepted (2026-11-28)
- **Date:** 2026-11-27

## Context

A React Flow canvas can represent either the audio pipeline (mic → VAD → STT → LLM → TTS) or the conversation itself (steps, branches, tools). People building voice agents struggle with conversation control, not with wiring audio components, which have sensible defaults.

## Decision

The canvas is a **conversation workflow**. Node catalogue v1: Start, Agent step, Extract, Router, Tool call, Handoff, End, Note. Edges out of Agent step and Router carry a condition: LLM-judged natural language, a CEL expression over session variables, or `else`. Edges are evaluated in stored order with CEL before LLM conditions, and all LLM conditions of one node are judged in a single batched call. Pipeline choices (STT, LLM, TTS, turn-taking) are agent settings, overridable per Agent step.

## Consequences

The graph schema becomes the core contract shared by builder and runtime (see ADR-0008). CEL needs matching Python and JavaScript implementations, verified against a shared conformance test file. Custom node types are deferred to v2 so the schema can settle.

## Alternatives considered

Pipeline graph like ComfyUI or Langflow (powerful but not what users need); both views (double the UI work); JSONLogic or JavaScript expressions instead of CEL (less readable, or unsafe).
