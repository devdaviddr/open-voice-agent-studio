# Changelog

All notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-11-28

The MVP (`spec/mvp`).

### Added
- Accounts and workspaces: email and password sign-up, sign-in and sign-out; the first user owns
  the workspace; open sign-up setting; rate-limited sign-in and origin checks.
- Agent builder on a React Flow canvas: Start, Agent step, Extract, Router, End and Note nodes;
  conditions as plain language, CEL expressions or `else`; typed variables; validation on the
  canvas; autosave with conflict detection; undo, redo, copy and paste; a receptionist template.
- Versions: publish immutable versions, a live pointer, restore and diff.
- Workflow engine and runtime: streaming replies over a WebSocket, edge evaluation (expressions,
  then one LLM judgement, then `else`), variable extraction with type checks, history budget with
  summaries.
- Test console: run the draft or any version, test caller IDs, live events, read-aloud with
  Kokoro, push-to-talk with Whisper, and canvas animation of what the agent is doing.
- Sessions: every console conversation stored with its transcript, events and version.
- Knowledge base: upload Markdown, text and PDF; local chunking and embeddings
  (bge-small-en-v1.5, pgvector); attach to agents, narrow per step, `search_knowledge` tool and
  automatic top passages.
- Long-term memory: facts extracted after each session per agent and caller, recalled in the next
  session and by the `recall_memory` tool; list and delete in the studio.
- Workspace LLM setting for any OpenAI-compatible endpoint, with the key stored encrypted.
- Quality gates: CI with lint, types, codegen drift, tests, an 80% API coverage floor, image builds
  and Playwright end-to-end tests against a scripted stub LLM.
- Documentation: getting started, concepts, architecture, accepted ADRs 0001–0020.

### Changed
- The Rust audio service and the original skeleton were replaced by the monorepo layout
  (ADR-0005, ADR-0008).

## [0.2.0] - 2026-11-27

Foundation (`spec/m0-foundation`): monorepo, Postgres with pgvector and migrations, the
`AgentSpec` schema with generated TypeScript types, Kokoro text-to-speech, contributor setup.

## [0.1.0] - 2026-11-27

Initial skeleton: React frontend, Python agent service, Rust audio service, Docker Compose.

[0.3.0]: https://github.com/devdaviddr/open-voice-agent-studio/releases/tag/v0.3.0
