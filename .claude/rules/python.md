---
paths:
  - "**/*.py"
---
# Python

- Python 3.12, typed everywhere; `pyright` (standard mode) must pass. No `Any` unless at a boundary.
- Ruff formats and lints (line length 100). The edit hook runs it; fix what it reports.
- Async all the way in services: SQLAlchemy `AsyncSession`, `httpx.AsyncClient`. No blocking I/O in
  request handlers; push CPU-heavy work (embedding, PDF parsing) to `asyncio.to_thread` or a job.
- Pydantic v2 models for every request and response body; no bare dicts across API boundaries.
- Import from the package root name (`ovas_api.…`), never relative imports across packages.
- Catch the narrowest exception; never swallow an exception without logging or re-raising.
