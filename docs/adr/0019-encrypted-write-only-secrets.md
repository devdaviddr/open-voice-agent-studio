# ADR-0019: Encrypted, write-only secrets

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Webhook tools, MCP servers and providers need API keys. Keys in plain configuration leak through exports, logs and screenshots.

## Decision

Secrets are stored encrypted with AES-GCM under a master key from `OVAS_SECRET_KEY`. The API can create, replace and delete them but never returns their values. Configuration refers to them as `{{secrets.NAME}}`, resolved only inside the runtime or API at call time. Logs and session events redact resolved values.

## Consequences

Losing `OVAS_SECRET_KEY` means re-entering secrets, which is documented. Agent exports (YAML) carry references, never values.

## Alternatives considered

Plain environment variables per tool (no UI management, easy to leak).
