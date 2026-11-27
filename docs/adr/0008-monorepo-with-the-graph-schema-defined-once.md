# ADR-0008: Monorepo with the graph schema defined once

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

The builder (TypeScript) and the runtime and API (Python) must agree exactly on the shape of an agent. Hand-maintained types in two languages drift.

## Decision

One repository with a pnpm workspace (`apps/*`, `packages/*` for JS) and a uv workspace (`services/*`, `packages/core`, `providers/*`). The `AgentSpec` schema lives only in `ovas-core` as Pydantic models; `make gen` exports JSON Schema and generates TypeScript types into the web app, and `make gen-check` fails CI if they are stale. The REST client for the web app is generated from the API's OpenAPI document in the same way.

## Consequences

Schema changes are one edit plus `make gen`. Generated files are committed so diffs are reviewable.

## Alternatives considered

Separate repositories (version skew); schema authored in TypeScript (the runtime is Python, where validation matters most).
