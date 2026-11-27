# ADR-0004: Pipecat runtime over WebRTC

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

Real-time voice needs voice activity detection, end-of-turn detection, interruption handling, streaming between providers and a browser transport. Building this well takes months.

## Decision

The runtime uses **Pipecat**. A published `AgentSpec` is compiled into a Pipecat pipeline per session, with our workflow engine controlling the LLM context and tools as the session moves through nodes. Browsers connect through Pipecat's small WebRTC transport, so no separate media server is required. The Pipecat version is pinned and wrapped behind one pipeline-builder module.

## Consequences

We inherit Pipecat's provider ecosystem and turn-taking (Silero VAD, smart-turn). Pipecat upgrades are contained to one module. Telephony in v2 can use Pipecat's Twilio and SIP transports.

## Alternatives considered

LiveKit Agents (excellent turn detection, but needs a LiveKit server); a custom runtime (months of work on solved problems).
