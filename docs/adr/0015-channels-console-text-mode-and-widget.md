# ADR-0015: Channels: console, text mode and widget

- **Status:** Accepted (2026-11-28)
- **Date:** 2026-11-27

## Context

Builders need to test agents; site owners need to embed them; phone calls are a large separate integration.

## Decision

v1 ships a studio test console (voice or text, live transcript, active node, tool calls, latency), a text mode for every agent, and an embeddable widget as a web component (`<ovas-agent>`) with theming. Phone calls through Twilio or SIP are v2.

## Consequences

Text mode also makes v1.1 evaluations cheap. Phone users wait for v2.

## Alternatives considered

Phone in v1 (delays everything else).
