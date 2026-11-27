---
feature: m0-foundation
title: M0 Foundation
version: 0.1.0
status: draft
owner: devdaviddr
created: 2026-11-27
updated: 2026-11-27
---

# M0 Foundation — Specification

> **Stage 1 · SPECIFY.** Milestone M0 of `spec/product`. It builds no product features. It turns
> the skeleton into a repo that humans and AI agents can build v1 in, safely and consistently.

## 1. Problem & context

The repo today is a skeleton: a Vite frontend, a FastAPI `agent` service, an empty Rust `audio`
service and a Kokoro `tts` service, each with its own ad hoc commands. There is no shared schema,
no database, no written architecture, no process, and no guardrails for the AI agents that will do
most of the building. Without those, M1–M5 would drift from the product spec and from each other.

## 2. Goals

- The repo layout matches the product architecture (`spec/product/0.1.0/plan.md` §3).
- One command starts the stack, one command runs every check, and the same checks run in git hooks,
  Claude Code hooks and CI.
- The workflow graph schema exists once, in Python, and the TypeScript types are generated from it
  with a drift check.
- An AI agent dropped into the repo finds the rules, the process and the recipes for common changes
  without being told.
- A new contributor can read the README and docs and get running in under 15 minutes.

## 3. Non-goals

- Any product feature from `spec/product` (accounts, builder, runtime voice loop, tools). Those are
  M1+.
- Database tables beyond the migration baseline.
- A docs website, release automation, container publishing.

## 4. User scenarios

- As a **contributor**, I want `make dev` and `make check` to just work, so that I don't learn five
  toolchains before my first PR.
- As an **AI coding agent**, I want CLAUDE.md, path-scoped rules and skills, so that I follow the
  project's conventions and the spec process without being reminded.
- As the **maintainer**, I want hooks that format, lint and test automatically, so that agent-written
  code arrives already passing.
- As a **reviewer**, I want CI on every PR, so that I never merge red code.

## 5. Functional requirements

### Layout
- **FR-1.** The repo MUST use this top-level layout: `apps/web`, `services/api`, `services/runtime`,
  `packages/core`, `providers/tts-kokoro`, `spec/`, `docs/`, `scripts/`, `.claude/`, `.github/`.
- **FR-2.** The Rust `audio` service MUST be removed, with ADR-0005 recording why.
- **FR-3.** The existing TTS service MUST move to `providers/tts-kokoro` with unchanged behaviour
  (`/health`, `/voices`, `/tts`), and the existing `agent` service MUST become `services/api`.
- **FR-4.** `services/runtime` MUST exist as a FastAPI process with `/health`, ready for M2.
- **FR-5.** Python packages MUST form one uv workspace and JS packages one pnpm workspace, with a
  single lockfile each at the root.

### Stack and data
- **FR-6.** `docker compose up` MUST start web, api, runtime, tts-kokoro and Postgres 17 with
  pgvector, and the api `/health` MUST report the status of the database, runtime and tts.
- **FR-7.** `services/api` MUST have Alembic configured with a baseline migration that enables the
  `vector` extension, applied automatically on startup in development.

### Schema
- **FR-8.** `packages/core` (`ovas-core`) MUST define Pydantic v2 models for `AgentSpec` and
  everything in it as listed in `spec/product` §7 (settings, nodes, edges, conditions, variables,
  tool refs, knowledge refs).
- **FR-9.** `make gen` MUST export `AgentSpec` as JSON Schema and generate TypeScript types into
  `apps/web/src/gen/`, and `make gen-check` MUST fail when the generated files are out of date.

### Studio shell
- **FR-10.** `apps/web` MUST have TanStack Router and TanStack Query wired up, an app shell (sidebar,
  header, light/dark/system theme), an empty-state Agents page, a Services status page and a TTS
  playground page carrying the existing speak card.

### Commands and gates
- **FR-11.** A root `Makefile` MUST provide `dev`, `up`, `down`, `check`, `fmt`, `lint`, `typecheck`,
  `test`, `gen` and `gen-check`, and `make check` MUST run lint, typecheck, tests and gen-check for
  every package.
- **FR-12.** lefthook MUST run formatters and linters on staged files at pre-commit and `make check`
  at pre-push.
- **FR-13.** A GitHub Actions workflow MUST run `make check` on every pull request and push to
  `main`.

### Claude Code setup
- **FR-14.** A root `CLAUDE.md` MUST give the architecture map, commands, the spec-first rule and
  pointers to rules and skills; each of `apps/web`, `services/api`, `services/runtime`,
  `packages/core` and `providers/tts-kokoro` MUST have its own short `CLAUDE.md`. `AGENTS.md` MUST
  point other agents at the same instructions.
- **FR-15.** `.claude/rules/` MUST hold path-scoped rule files for Python, TypeScript/React, API
  design, database migrations, testing and the spec process.
- **FR-16.** `.claude/skills/` MUST provide skills `new-spec`, `add-node-type`, `add-provider`,
  `add-tool-type`, `db-migration` and `release`, each a step-by-step recipe naming the files to
  touch and the checks to run.
- **FR-17.** `.claude/settings.json` MUST configure hooks: after file edits, format and lint that
  file; before shell commands, block force-pushes to `main`, `git push --no-verify`, and writes to
  `.env*`; at the end of a turn, run fast tests for packages with changes; at session start, print
  the current spec versions and open tasks. It MUST also allow the project's check commands.

### Docs and contributing
- **FR-18.** The README MUST explain what the project is, show the architecture, give the quick
  start, link the docs and show project status against the milestones.
- **FR-19.** `docs/` MUST contain getting-started, concepts (agents, workflows, nodes, edges,
  versions, tools, memory, knowledge), architecture (with a diagram) and the ADR index.
- **FR-20.** The repo MUST include `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant
  2.1), `SECURITY.md`, `CHANGELOG.md`, issue templates (bug, feature) and a PR template that asks
  for the spec version, FR/AC IDs and checks run.
- **FR-21.** `scripts/spec_tool.py` MUST be vendored so contributors can run `init`, `bump`, `show`
  and `list`, and `spec/README.md` MUST explain the six-stage process.

## 6. Non-functional requirements

- **NFR-1.** `make check` on a warm cache completes in under 2 minutes on a laptop.
- **NFR-2.** The Claude after-edit hook completes in under 3 seconds for a single file, so it does
  not slow agents down.
- **NFR-3.** No secrets in the repo; `.env.example` documents every variable.
- **NFR-4.** The stack still starts with no GPU and no API keys.

## 7. Data model & contracts

```text
Makefile targets      dev | up | down | check | fmt | lint | typecheck | test | gen | gen-check
api GET /health  →    { "api": {status, version}, "db": {status}, "runtime": {status, version},
                        "tts": {status, version, model} }          # status: "ok" | "unreachable" | <detail>
runtime GET /health → { "status": "ok", "version": "0.2.0" }
Generated files       packages/core/schema/agent-spec.schema.json
                      apps/web/src/gen/agent-spec.ts
Env vars              OVAS_DATABASE_URL, OVAS_RUNTIME_URL, OVAS_TTS_URL, OVAS_API_URL (web dev proxy)
```

The `AgentSpec` models follow `spec/product/0.1.0/spec.md` §7 exactly.

## 8. Acceptance criteria

- **AC-1.** (FR-1, FR-2) Given the repo, then the FR-1 directories exist and no `audio/`, `Cargo.*`
  or Rust files remain.
- **AC-2.** (FR-3) Given the moved TTS service, then its existing tests pass and `POST /tts` returns
  WAV through the stack.
- **AC-3.** (FR-4, FR-6) Given `docker compose up`, then api `/health` reports `ok` for api, db,
  runtime and tts.
- **AC-4.** (FR-5) Given a clean clone, then `uv sync` and `pnpm install` at the root install every
  package, and each ecosystem has exactly one lockfile.
- **AC-5.** (FR-7) Given a fresh database, when the api starts, then `alembic current` is at the
  baseline head and `vector` is installed.
- **AC-6.** (FR-8) Given a sample `AgentSpec` with one node of each type, then it round-trips through
  the Pydantic models unchanged, and an unknown node type is rejected.
- **AC-7.** (FR-9) Given a change to a core model without `make gen`, then `make gen-check` fails;
  after `make gen` it passes, and the web app typechecks against the generated types.
- **AC-8.** (FR-10) Given the web app, then `/agents`, `/services` and `/playground/tts` render,
  the theme toggle persists, and a router/query smoke test passes in Vitest.
- **AC-9.** (FR-11) Given a clean clone after install, then every Makefile target in §7 exits 0 (with
  `dev`/`up` checked by health).
- **AC-10.** (FR-12) Given a staged Python file with a lint error, then the commit is rejected.
- **AC-11.** (FR-13) Given a PR, then the CI workflow runs `make check` and reports status.
- **AC-12.** (FR-14, FR-15) Given the repo, then every listed CLAUDE.md and rule file exists, each
  rule has a `paths` scope, and root CLAUDE.md is under 150 lines.
- **AC-13.** (FR-16) Given each skill, then its SKILL.md has a name, a trigger description, ordered
  steps and the checks to run.
- **AC-14.** (FR-17) Given the hooks, then: editing a badly formatted Python file leaves it formatted;
  `git push --force origin main` is blocked; writing `.env` is blocked; a turn ending with a broken
  test in a changed package reports the failure. Each is covered by a hook test script.
- **AC-15.** (FR-18, FR-19) Given the docs, then every page listed in FR-19 exists and every link in
  README and docs resolves (link check in `make check`).
- **AC-16.** (FR-20) Given the repo, then every file in FR-20 exists and the PR template asks for
  spec version, FR/AC IDs and checks run.
- **AC-17.** (FR-21) Given `scripts/spec_tool.py list`, then it lists `product` and `m0-foundation`.
- **AC-18.** (NFR-1, NFR-2) Given a warm cache, then `make check` takes under 2 minutes and the
  after-edit hook under 3 seconds on one file (timed in the hook test script).

## 9. Open questions

- None. All design choices were settled in the 2026-11-27 design session (see ADR-0001–0020).

## Changelog

| Version | Date | Level | Note |
| --- | --- | --- | --- |
| 0.1.0 | 2026-11-27 | init | Initial draft |
