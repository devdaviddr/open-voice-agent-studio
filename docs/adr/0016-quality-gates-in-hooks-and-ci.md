# ADR-0016: Quality gates in hooks and CI

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Code arrives from humans and from AI agents. Checks that only run in CI are found late; checks that only run locally can be skipped.

## Decision

The same `make check` (lint, typecheck, tests, codegen drift, link check) runs in three places: lefthook at pre-push (with staged-file format and lint at pre-commit), Claude Code hooks (format and lint after each edit, tests for changed packages at the end of a turn, guards against force-pushes and secret files), and one GitHub Actions workflow on pull requests. Docs live in the repo (`docs/`), with no separate docs site or wiki until v1.0.

## Consequences

Agent-written code arrives already formatted and tested. Hooks must stay fast (under 3 s per edit).

## Alternatives considered

Local checks only (contributors expect CI on a public repo); CI only (slow feedback for agents).
