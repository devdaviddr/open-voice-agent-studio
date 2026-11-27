---
paths:
  - "services/api/**"
---
# API design

- Routes under `/v1`, grouped by resource in `ovas_api/routes/<resource>.py`.
- Every handler takes the current user via the `CurrentUser` dependency and filters by its
  `workspace_id`. Cross-workspace access returns 404, not 403.
- Errors: raise `HTTPException` with a message that says what to do. 409 for revision conflicts,
  422 for validation, 429 for rate limits.
- Response models never include secret values; secrets serialise as `{"set": true|false}`.
- The studio uses only public endpoints (ADR-0020). Internal endpoints live under `/internal` and
  require `OVAS_INTERNAL_KEY`.
- Every new endpoint gets a test in `services/api/tests/` that names the AC it covers.
