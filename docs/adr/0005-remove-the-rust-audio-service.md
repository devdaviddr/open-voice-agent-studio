# ADR-0005: Remove the Rust audio service

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

The initial skeleton included a Rust (Axum) audio service with only a health endpoint. With Pipecat (ADR-0004) all audio handling stays in Python, and Rust is not installed on the main development machine.

## Decision

Remove the Rust service. Rust may return when profiling shows a hot path Python cannot meet, such as audio mixing at scale or a phone media gateway; that would be a new ADR with measurements.

## Consequences

One fewer toolchain in CI and for contributors. No empty service inviting questions.

## Alternatives considered

Keep an empty placeholder; give it a speculative job now (a gateway with no users).
