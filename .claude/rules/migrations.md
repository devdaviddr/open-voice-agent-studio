---
paths:
  - "services/api/migrations/**"
  - "services/api/src/ovas_api/models.py"
---
# Database migrations

- Change `models.py`, then generate: `cd services/api && uv run alembic revision --autogenerate -m "<what>"`
  against a database at head. Review the generated file; autogenerate misses extensions, triggers
  and vector indexes.
- Number revisions sequentially (`0002_auth.py`, revision id `"0002"`).
- Every table has `workspace_id` (except `workspaces`, `users`) with an index.
- Every migration has a working `downgrade()`; tests run downgrade → upgrade on each run.
- Never edit a migration that is on `main`; add a new one.
