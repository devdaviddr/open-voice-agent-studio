# providers/stt-whisper — Whisper speech-to-text

`POST /stt` (raw audio body, any format PyAV decodes; `?language=`) → `{text, language,
duration_ms}`. faster-whisper on CPU (int8). Model `OVAS_WHISPER_MODEL` (default `base`) downloads on
first request into `MODELS_DIR`. Tests use a fake engine and never load the model.
