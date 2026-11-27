# ADR-0001: Record architecture decisions

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Design decisions for this project were made in one long design session and will keep being made by humans and AI agents. Without a record, agents re-open settled questions and contributors cannot see why the code looks the way it does.

## Decision

We record each significant decision as a numbered ADR in `docs/adr/`, using this short format (context, decision, consequences, alternatives). ADRs are immutable once accepted; a later ADR supersedes an earlier one and both link to each other. Product and milestone specs in `spec/` cite ADRs instead of repeating them.

## Consequences

Reviewers can point at an ADR instead of re-arguing. Agents are told in CLAUDE.md to read the relevant ADR before proposing an architectural change.

## Alternatives considered

Decisions only in PR descriptions (hard to find); a single DECISIONS.md (grows unreadable).
