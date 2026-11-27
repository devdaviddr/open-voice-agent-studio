# apps/web — studio UI

`pnpm --filter @ovas/web dev` (or `make dev`). Vite proxies `/api/*` to the API (`OVAS_API_URL`).

- `src/gen/` is generated (`make gen`); read-only.
- Routes: TanStack Router in `src/routes/`. Data: TanStack Query hooks in `src/api/`.
- Builder canvas: React Flow 13 (`@xyflow/react`). Dark mode follows the `.dark` class on `<html>`;
  React Flow picks it up from CSS, there is no `colorMode` prop in v13.
- shadcn style is `base-nova` (Base UI primitives); `cn` comes from the `cn` package.
- Checks: `pnpm --filter @ovas/web lint`, `typecheck`, `test`.
