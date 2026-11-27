# Open Voice Agent Studio

An open-source studio for building, running and testing voice agents.

> Early days: text-to-speech works (Kokoro-82M). Speech-to-text and the agent loop are next.

## Architecture

| Service    | Stack                                  | Port | Role                                          |
|------------|----------------------------------------|------|-----------------------------------------------|
| `frontend` | React, TypeScript, Vite, Tailwind, shadcn/ui | 5173 | Studio UI                              |
| `agent`    | Python 3.12, FastAPI, uv               | 8000 | Agent orchestration (speech-to-text, LLM, text-to-speech) |
| `audio`    | Rust, Axum, Tokio                      | 8001 | Low-latency audio streaming                   |
| `tts`      | Python 3.12, FastAPI, [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) | 8002 | Text-to-speech, 54 voices, CPU |

The frontend proxies `/api/*` to the agent. The agent calls the audio and tts services.

### Text-to-speech API

```sh
curl localhost:8000/voices
curl -X POST localhost:8000/tts -H 'content-type: application/json' \
  -d '{"text": "Hello there.", "voice": "af_heart", "speed": 1.0}' -o hello.wav
```

Returns 24 kHz mono 16-bit WAV. `text` is up to 5000 characters and `speed` ranges from 0.5 to 2.0.

## Quick start

```sh
docker compose up --build
```

Open http://localhost:5173. The Services card should show `agent`, `audio` and `tts` as `ok`. The text-to-speech card speaks whatever you type.

On first start the tts service downloads the Kokoro model files (about 350 MB) into the `kokoro-models` Docker volume. Until that finishes, `tts` reports `models missing`.

## Local development

```sh
# frontend
cd frontend && pnpm install && pnpm dev

# agent
cd agent && uv sync && uv run uvicorn agent.main:app --reload --port 8000

# audio (needs a Rust toolchain)
cd audio && cargo run

# tts
cd tts && scripts/fetch-models.sh && uv sync && uv run uvicorn tts.main:app --reload --port 8002
```

## Checks

```sh
cd frontend && pnpm build && pnpm lint
cd agent && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd tts && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd audio && cargo build
```

## License

MIT. Kokoro-82M model weights are Apache 2.0.
