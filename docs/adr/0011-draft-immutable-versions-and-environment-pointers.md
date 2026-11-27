# ADR-0011: Draft, immutable versions and environment pointers

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Users need to change live agents safely, roll back quickly and know exactly what answered a given conversation.

## Decision

Each agent has one editable draft. Publishing freezes the draft into an immutable, sequentially numbered version with a message, author and full snapshot (graph, settings, and copies of the tool and knowledge configuration it uses; secrets stay references). Environments (`live`, optionally `staging` and others) point at versions; rollback moves a pointer. Every session records its version or draft revision. Diffs are computed at node, edge, setting and prompt level. No git-style branches in v1.

## Consequences

Published agents never change under users. Snapshots cost storage, which is small (JSON). Branches and A/B splits come in v2.

## Alternatives considered

Git-style branches and merges (complex UI); referencing tools by ID instead of snapshotting (silent behaviour changes).
