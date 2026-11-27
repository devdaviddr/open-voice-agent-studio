# Specs

This project uses spec-driven development (ADR-0007). Code follows an approved spec.

```
SPECIFY → PLAN → BREAK INTO TASKS → IMPLEMENT → TEST → MAINTAIN
```

Each feature has versioned snapshot directories: `spec/<feature>/<semver>/{spec,plan,tasks}.md`.
The highest version is current; older ones are frozen history.

| Feature | What |
| --- | --- |
| `product/` | The v1 product contract: FR-1–FR-35, milestones |
| `mvp/` | The first usable release (0.3.0): what is being built now |
| `m0-foundation/` | Repo foundations (layout, checks, Claude setup) |

## Workflow

1. `python3 scripts/spec_tool.py init --title "…" --feature <slug> --root spec/<slug>` scaffolds
   `0.1.0` (draft).
2. Fill `spec.md` (problem, FR-N, AC-N), then `plan.md`, then `tasks.md`.
3. Open a PR. **Merging it is the approval**; the maintainer then bumps it:
   `python3 scripts/spec_tool.py bump major --note "Approved" --status approved --root spec/<slug>`.
4. Implement tasks in order; tests name the AC they cover.
5. Scope change: bump first (`major` breaks, `minor` adds, `patch` clarifies), then code.

`python3 scripts/spec_tool.py list --root spec/<slug>` shows versions and status.
