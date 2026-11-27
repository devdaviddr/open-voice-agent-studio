---
feature: m0-foundation
title: M0 Foundation
version: 0.1.0
status: draft
updated: 2026-11-27
---

# M0 Foundation — Implementation Plan

> **Stage 2 · PLAN.** How M0 is built. Product-level choices are in `spec/product/0.1.0/plan.md` and
> the ADRs; this file only adds what M0 needs.

## 1. Approach summary

Move code before adding code: first restructure into the target layout with behaviour unchanged,
then put the workspaces, Makefile and gates around it, then add the schema, database and studio
shell, and last the Claude setup and docs, which describe the finished structure.

## 2. Technology choices

| Area | Choice | Why | Alternative considered |
| --- | --- | --- | --- |
| Task runner | GNU Make | Preinstalled everywhere; thin wrapper over uv/pnpm | just, Taskfile (extra install) |
| Python | 3.12, uv workspace, ruff (lint + format), pyright (typecheck), pytest | Fast, one tool per job | poetry, mypy |
| JS | Node 22, pnpm 11 workspace, oxlint, Prettier, `tsc -b`, Vitest | Matches existing frontend | eslint (slower) |
| Codegen | Pydantic `model_json_schema()` → `json-schema-to-typescript` | Mature, no custom generator | datamodel-code-generator (wrong direction) |
| Git hooks | lefthook | Single binary, parallel, staged-file globs | pre-commit (Python-only feel), husky |
| CI | GitHub Actions, one job, cached uv and pnpm | Lean; public repo minutes are free | Matrix per package |
| DB | `pgvector/pgvector:pg17` image, SQLAlchemy 2 async + asyncpg, Alembic | Per ADR-0010 | — |
| Router/data | TanStack Router (code-based routes), TanStack Query | Per ADR-0014 | — |
| Link check | `lychee` in offline mode (local links only) | Fast, no network | markdown-link-check |

## 3. Architecture

```
open-voice-agent-studio/
├─ apps/web/                   Vite + React + shadcn studio (moved from frontend/)
│  └─ src/{routes,components,gen,lib}
├─ services/api/               FastAPI control plane (moved from agent/), Alembic in migrations/
├─ services/runtime/           FastAPI runtime skeleton (/health)
├─ packages/core/              ovas-core: Pydantic AgentSpec + schema export
├─ providers/tts-kokoro/       moved from tts/
├─ spec/  docs/{adr,…}  scripts/{spec_tool.py,gen.sh,hooks/}
├─ .claude/{settings.json,rules/,skills/,hooks/}
├─ .github/{workflows/ci.yml,ISSUE_TEMPLATE/,pull_request_template.md}
├─ CLAUDE.md  AGENTS.md  README.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md  CHANGELOG.md
├─ Makefile  lefthook.yml  docker-compose.yml  .env.example
├─ pyproject.toml (uv workspace root)  uv.lock
└─ package.json + pnpm-workspace.yaml  pnpm-lock.yaml
```

Python package names: `ovas-core`, `ovas-api`, `ovas-runtime`, `ovas-tts-kokoro`; import names
`ovas_core`, `ovas_api`, `ovas_runtime`, `ovas_tts_kokoro`.

### Claude Code hooks (`.claude/hooks/`, shell + Python, no network)

| Event | Matcher | Script | Behaviour |
| --- | --- | --- | --- |
| PostToolUse | `Edit\|Write` | `format-file.sh` | ruff format + ruff check --fix on `.py`; prettier + oxlint on `.ts/.tsx`; reports remaining problems back to Claude |
| PreToolUse | `Bash` | `guard-bash.py` | Blocks `git push` with `--force`/`-f` to `main`, `--no-verify`, and redirects into `.env*` |
| PreToolUse | `Edit\|Write` | `guard-files.py` | Blocks edits to `.env*`, lockfiles (must change through the package manager), and files under `spec/*/<frozen version>/` once that version is approved |
| Stop | — | `test-changed.sh` | Runs fast tests only for packages with uncommitted changes; non-zero exit sends failures back to Claude |
| SessionStart | — | `spec-status.sh` | Prints `spec_tool.py list` and the unchecked tasks of the current milestone |

Hook tests live in `scripts/hooks/test_hooks.py` and run in `make check` (AC-14, AC-18).

### Rules (`.claude/rules/*.md`, each with `paths:` frontmatter)

`python.md` (`**/*.py`), `typescript-react.md` (`apps/**/*.{ts,tsx}`), `api.md`
(`services/api/**`), `migrations.md` (`services/api/migrations/**`), `testing.md`
(`**/tests/**`, `**/*.test.ts*`), `spec-process.md` (`spec/**`, `docs/adr/**`).

## 4. Data & contracts

As spec §7. Compose services and ports: web 5173, api 8000, runtime 8100, tts-kokoro 8002, postgres
5432 (internal only; not published to the host). Volumes: `pgdata`, `kokoro-models`.

## 5. Key decisions & trade-offs

- **DD-1.** Restructure with `git mv` so history follows the files.
- **DD-2.** Generated files are committed (reviewable diffs) and guarded by `gen-check`.
- **DD-3.** Runtime moves to port 8100 to leave room for one port per future provider in 8001–8099.
- **DD-4.** Postgres is not published to the host by default; `docker compose exec db psql` is
  documented instead. Avoids clashes with local Postgres installs.
- **DD-5.** Hooks are fast-path only; the full suite runs at pre-push and in CI.

## 6. Risks & mitigations

- **Risk:** Moving packages breaks Docker builds. **Mitigation:** AC-3 checks the full stack after
  T-1.
- **Risk:** Hooks annoy agents with false positives. **Mitigation:** hook tests (AC-14), explicit
  messages saying what to do instead.
- **Risk:** Generated TS types are awkward for discriminated unions. **Mitigation:** Pydantic
  `Field(discriminator="type")`; check generated output in T-6 and adjust model config.

## 7. Rollout & observability

- Delivered as one PR per task group (see `tasks.md`), each passing `make check`.
- On completion: bump `spec/m0-foundation` to `implemented`, release app version **0.2.0** with a
  CHANGELOG entry and a git tag.
