# ADR-0018: Observability and data retention

- **Status:** Accepted (2026-11-28)
- **Date:** 2026-11-27

## Context

Debugging voice agents needs more than transcripts: which node was active, which edge fired, which tool ran with what, and where latency came from. Operators also need to control how long personal data is kept.

## Decision

Each session stores its transcript, an ordered event timeline (node changes, edge decisions, tool calls and results, variable changes, interruptions, errors), per-turn latency (STT, LLM time to first token, TTS time to first byte), token and character usage, and its version. Audio recording is opt-in per agent. API and runtime can export OpenTelemetry traces to any collector; none is bundled. Retention is set per workspace (recordings default 30 days); deleting a session deletes its memories too.

## Consequences

Everything needed to debug lives in Postgres and the console. No observability stack to run by default.

## Alternatives considered

Bundling a tracing stack (heavy for self-hosters); transcripts only (not enough to debug workflows).
