---
paths:
  - "apps/**/*.ts"
  - "apps/**/*.tsx"
---
# TypeScript and React

- Strict TS; no `any`, no non-null `!` except on DOM roots. Types for the agent graph come from
  `@/gen/agent-spec` and API types from `@/gen/api`; never redeclare them.
- Server state: TanStack Query hooks in `src/api/`. Builder (canvas) state: the Zustand store in
  `src/builder/store.ts`. No fetch calls inside components.
- UI from `src/components/ui` (shadcn on Base UI). Add new primitives with
  `pnpm dlx shadcn@latest add <name>`; do not hand-roll a button or dialog.
- Styling with Tailwind tokens (`bg-background`, `text-muted-foreground`…); never hard-code colours
  that break dark mode.
- Every interactive element is reachable by keyboard and has an accessible name.
- Tests: Vitest + Testing Library next to the file (`*.test.tsx`); test behaviour, not markup.
