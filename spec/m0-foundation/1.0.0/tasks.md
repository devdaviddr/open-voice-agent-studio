---
feature: m0-foundation
title: M0 Foundation
version: 1.0.0
status: approved
updated: 2026-11-28
---
# M0 Foundation — Task Backlog

> **Stage 3 · BREAK INTO TASKS.** Ordered, testable slices. One PR per PR group; each PR passes
> `make check` (from T-3 on) and names the tasks and ACs it covers.

## How to use
- Work top to bottom; respect `depends on`.
- A task is **done** only when its linked acceptance criteria pass.
- If a task reveals a spec gap, update `spec.md`/`plan.md` and **bump the version first**.

## Backlog

| # | Task | Serves | Depends on | Verify by | PR | Done |
| --- | --- | --- | --- | --- | --- | --- |
| T-1 | `git mv` into the target layout (frontend→apps/web, agent→services/api, tts→providers/tts-kokoro); delete `audio/`; rename Python packages to `ovas_*`; fix Dockerfiles and compose | FR-1, FR-2, FR-3 | — | AC-1, AC-2 | A | [ ] |
| T-2 | Root uv workspace and pnpm workspace; single lockfiles | FR-5 | T-1 | AC-4 | A | [ ] |
| T-3 | Root Makefile with all targets; pyright and Prettier added | FR-11 | T-2 | AC-9 | A | [ ] |
| T-4 | `services/runtime` skeleton with `/health` and test | FR-4 | T-2 | AC-3 | B | [ ] |
| T-5 | Postgres (pgvector) in compose; api DB session, Alembic baseline enabling `vector`; `/health` aggregates db, runtime, tts | FR-6, FR-7 | T-4 | AC-3, AC-5 | B | [ ] |
| T-6 | `ovas-core` AgentSpec models with round-trip and rejection tests | FR-8 | T-2 | AC-6 | C | [ ] |
| T-7 | `make gen` / `gen-check`: JSON Schema export + TS generation; web typechecks against it | FR-9 | T-6, T-3 | AC-7 | C | [ ] |
| T-8 | Studio shell: TanStack Router + Query, sidebar layout, theme toggle, Agents empty state, Services page, TTS playground; Vitest smoke test | FR-10 | T-7 | AC-8 | D | [ ] |
| T-9 | lefthook (pre-commit staged lint/format, pre-push `make check`) | FR-12 | T-3 | AC-10 | E | [ ] |
| T-10 | GitHub Actions `ci.yml` running `make check` with uv/pnpm caches | FR-13 | T-3 | AC-11 | E | [ ] |
| T-11 | Root and per-package CLAUDE.md, AGENTS.md, `.claude/rules/*` | FR-14, FR-15 | T-8 | AC-12 | F | [ ] |
| T-12 | Claude hooks + `.claude/settings.json` + hook test script | FR-17 | T-3 | AC-14, AC-18 | F | [ ] |
| T-13 | Skills: new-spec, add-node-type, add-provider, add-tool-type, db-migration, release | FR-16 | T-11 | AC-13 | F | [ ] |
| T-14 | README rewrite; docs: getting-started, concepts, architecture (diagram); link check in `make check` | FR-18, FR-19 | T-8 | AC-15 | G | [ ] |
| T-15 | CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG, issue + PR templates | FR-20 | — | AC-16 | G | [ ] |
| T-16 | Vendor `scripts/spec_tool.py`; `spec/README.md` | FR-21 | — | AC-17 | G | [ ] |
| T-17 | Time `make check` and the edit hook; bump spec to `implemented`; release 0.2.0 | NFR-1, NFR-2 | all | AC-18 | H | [ ] |

PR groups: **A** restructure · **B** runtime + database · **C** schema + codegen · **D** studio
shell · **E** git hooks + CI · **F** Claude setup · **G** docs + contributing + SDD tooling ·
**H** release.

## Definition of done (this version)
- [ ] Every functional requirement (FR-1–FR-21) has at least one task.
- [ ] Every acceptance criterion (AC-1–AC-18) has a verifying test or check.
- [ ] All tasks checked off and `make check` passing in CI.
- [ ] `spec.md` and `plan.md` still match what was built (else bump + reconcile).