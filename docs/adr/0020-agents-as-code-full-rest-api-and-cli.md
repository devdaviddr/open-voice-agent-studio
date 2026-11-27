# ADR-0020: Agents as code: full REST API and CLI

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Teams want agent changes reviewed like code, and automation needs everything the UI can do.

## Decision

Every studio capability is exposed through a versioned, documented REST API (OpenAPI) that the studio itself uses, with no private endpoints. An `ovas` CLI exports and imports agents as YAML (`pull`, `push`, `publish`, `diff`) so agents can live in git. This complements built-in versioning; publishing still creates immutable versions.

## Consequences

The API surface is a public contract and changes follow semver.

## Alternatives considered

UI-only management (locks users in).
