---
paths:
  - "**/tests/**"
  - "**/*.test.ts"
  - "**/*.test.tsx"
---
# Tests

- Name each test after the behaviour and tag the acceptance criterion: `def test_stale_revision_conflicts():  # MVP AC-6`.
- API tests hit a real Postgres (`make test-db`), never SQLite or mocks of the ORM.
- Tests never call a real model. Engine and runtime tests use `ovas_core.testing.FakeLlm`; API
  tests use an `httpx.MockTransport` that answers like `/chat/completions`; the end-to-end suite
  (`make e2e`) runs the scripted OpenAI-compatible server in `services/runtime/tests/stub_llm.py`.
- `make test` fails below 80% API line coverage (NFR-1). Coverage traces greenlets, which the async
  SQLAlchemy engine runs in.
- End-to-end tests live in `apps/web/e2e/*.e2e.ts` (Playwright) and name the ACs they cover.
- A bug fix starts with a failing test.
