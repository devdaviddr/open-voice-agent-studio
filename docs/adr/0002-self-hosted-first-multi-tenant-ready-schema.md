# ADR-0002: Self-hosted first, multi-tenant-ready schema

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

The project could target a single self-hosted team (like n8n or Langflow) or a multi-tenant platform that someone could run as a hosted service. Multi-tenant features (org admin, quotas, billing) are a large amount of work that does not help the first users.

## Decision

v1 is self-hosted with one workspace per install. Every table carries `workspace_id` from the first migration and every query is scoped by it, and users have roles per workspace (`owner`, `member`). Multi-tenant administration is out of scope until v2.

## Consequences

No schema rewrite when multi-tenant arrives. Slight overhead now: every query and test is workspace-scoped (product AC-2 checks isolation).

## Alternatives considered

Multi-tenant from day one (slows v1 by months); single-tenant with no workspace concept (painful migration later).
