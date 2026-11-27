---
paths:
  - "**/tests/**"
  - "**/*.test.ts"
  - "**/*.test.tsx"
---
# Tests

- Name each test after the behaviour and tag the acceptance criterion: `def test_stale_revision_conflicts():  # MVP AC-6`.
- API tests hit a real Postgres (`make test-db`), never SQLite or mocks of the ORM.
- LLM calls in tests go to the stub server in `services/runtime/tests/stub_llm.py`; tests never
  call a real model.
- A bug fix starts with a failing test.
