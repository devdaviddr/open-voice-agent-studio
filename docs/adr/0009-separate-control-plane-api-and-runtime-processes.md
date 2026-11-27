# ADR-0009: Separate control-plane API and runtime processes

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

CRUD traffic (agents, versions, tools) is light and short-lived. Voice sessions are long-lived, CPU-heavy and latency-sensitive. Mixing them means a slow migration or a busy session can hurt the other.

## Decision

Two processes: `services/api` (control plane, owns the database schema) and `services/runtime` (sessions). They share `ovas-core`. The API issues a signed session token naming the agent, version and variables; the runtime loads that frozen version, runs the session and writes events. Runtimes are stateless between sessions and can scale out.

## Consequences

Clear failure boundaries and independent scaling. One more container in development.

## Alternatives considered

A single process (simpler now, entangled later).
