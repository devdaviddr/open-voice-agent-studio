# providers/tts-kokoro — Kokoro-82M TTS

`GET /voices`, `POST /tts` (24 kHz WAV). Model files (~350 MB) download on first start into
`MODELS_DIR` via `scripts/fetch-models.sh`. Tests use a fake engine and never load the model.
