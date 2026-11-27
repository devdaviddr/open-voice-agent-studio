# ADR-0014: Frontend stack

- **Status:** Accepted (2026-11-28)
- **Date:** 2026-11-27

## Context

The studio is an authenticated single-page app with a complex canvas. It has no SEO needs.

## Decision

Vite SPA with React and TypeScript, TanStack Router and TanStack Query, Zustand for builder state, React Flow 12 (`@xyflow/react`) for the canvas, shadcn/ui on Base UI with Tailwind v4, an API client generated from OpenAPI, and Vitest with Testing Library. Design is minimal and neutral with dark mode and keyboard-first interaction (command palette, shortcuts).

## Consequences

Fast builds and a simple deployment (static files). No server rendering.

## Alternatives considered

Next.js (server features we do not need); Redux (more ceremony than Zustand for canvas state).
