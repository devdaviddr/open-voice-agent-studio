---
paths:
  - "spec/**"
  - "docs/adr/**"
---
# Specs and ADRs

- Each `spec/<feature>/<semver>/` holds `spec.md` (what/why, FR, AC), `plan.md` (how) and
  `tasks.md` (ordered backlog). Approved and implemented versions are frozen; the guard hook blocks
  edits. Change scope with `python3 scripts/spec_tool.py bump <major|minor|patch> --note "…" --root spec/<feature>`.
- Bump levels: MAJOR breaks something specified, MINOR adds, PATCH clarifies.
- Never write a guess into a spec. Unknowns go in §9 Open questions or as `[NEEDS INPUT: …]`.
- Only the maintainer approves a spec (by merging its PR); agents never set `status: approved`.
- ADRs: copy the shape of an existing one; new ones start as Proposed.
