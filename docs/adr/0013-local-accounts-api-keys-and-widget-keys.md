# ADR-0013: Local accounts, API keys and widget keys

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

A self-hosted install needs sign-in without depending on an external identity provider, programmatic access for the CLI, and anonymous access for website visitors.

## Decision

Local accounts with email and argon2id-hashed passwords and HTTP-only session cookies. Workspace API keys (shown once, stored hashed) for the REST API and CLI. Widgets use a per-agent public key plus an allowed-origins list and can only start sessions for that agent. OIDC sign-in is a later addition.

## Consequences

Works offline. Operators who need SSO wait for OIDC.

## Alternatives considered

OIDC-only (requires an identity provider to try the product).
