# services/api — control plane

Run: `make up` (Docker) or `uv run uvicorn ovas_api.main:app --reload` with `OVAS_DATABASE_URL` set.

- Config: `ovas_api.config.Settings` (env prefix `OVAS_`). Document every new variable in `.env.example`.
- DB: `ovas_api.db` (async engine, `get_db` dependency). Models in `models.py`, migrations in `migrations/`.
- Tests need the test DB: `make test` (or `make test-db` then
  `OVAS_DATABASE_URL=postgresql+asyncpg://ovas:ovas@127.0.0.1:55432/ovas_test uv run pytest services/api`).
