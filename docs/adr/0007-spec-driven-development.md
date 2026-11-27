# ADR-0007: Spec-driven development

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Most code will be written by AI agents working from tickets. Without a written, versioned contract the build drifts from intent and nothing defines when a feature is done.

## Decision

We follow a six-stage process (specify, plan, break into tasks, implement, test, maintain). Each feature or milestone has `spec/<feature>/<semver>/{spec,plan,tasks}.md`; code starts only after the spec is approved; every task and test cites the FR/AC it serves; scope changes bump the spec version first. `scripts/spec_tool.py` manages versions.

## Consequences

Slower start per milestone; much less rework. The spec doubles as the acceptance test list and as context for agents.

## Alternatives considered

Issue-driven development without specs; one big design document that goes stale.
