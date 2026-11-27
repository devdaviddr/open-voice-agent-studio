# ADR-0006: Local-first providers behind a plugin interface

- **Status:** Proposed
- **Date:** 2026-11-27

## Context

The project promises to be completely open. Cloud speech and LLM providers give higher quality with less setup, but would make the default install depend on paid, closed services.

## Decision

Defaults are local: Kokoro-82M for TTS, faster-whisper for STT (`large-v3-turbo` on GPU, `small.en` on CPU), Silero VAD plus smart-turn, fastembed `bge-small-en-v1.5` for embeddings, and any OpenAI-compatible LLM endpoint. Compose ships an optional `local-llm` profile with Ollama. Providers implement a small interface and register through the Python entry-point group `ovas.providers`, so cloud providers (OpenAI, Anthropic, Deepgram, ElevenLabs, Cartesia, …) and third-party ones install as plugins. Heavy model servers run as separate containers under `providers/`.

## Consequences

A default install works offline with no keys (product FR-18). Quality on CPU is lower than cloud; latency is measured per turn so the trade-off is visible.

## Alternatives considered

Cloud-first (not open by default); local-only (blocks users who want quality providers).
