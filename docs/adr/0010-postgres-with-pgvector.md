# ADR-0010: Postgres with pgvector

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

We need relational data (workspaces, agents, versions, sessions, events) and vector search (knowledge base, long-term memory).

## Decision

Postgres 17 with the pgvector extension, accessed through SQLAlchemy 2 (async, asyncpg) with Alembic migrations. Embeddings are `vector(384)` to match the default embedding model; a different model means a new column and a migration.

## Consequences

One database to back up and operate. Postgres is a heavier dependency than SQLite for tiny installs, accepted for simplicity of one store.

## Alternatives considered

SQLite plus a separate vector database (two stores, weaker concurrency).
