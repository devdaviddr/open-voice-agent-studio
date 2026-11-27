# ADR-0012: Four tool types

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Agents need to act on external systems, on the page that embeds them, and on their own conversation.

## Decision

v1 supports **webhook** tools (JSON Schema parameters, HTTP call, secret references), **MCP** servers (tools discovered from the server; HTTP transport from the UI, stdio only through operator configuration), **client** tools (events to the embedding page through the widget SDK) and **built-in** tools (end session, go to node, set variable). Tools are attached per agent and narrowed per Agent step.

## Consequences

MCP gives instant access to a large ecosystem. stdio MCP is restricted because it executes commands on the host.

## Alternatives considered

Webhooks only (forces users to write glue servers).
