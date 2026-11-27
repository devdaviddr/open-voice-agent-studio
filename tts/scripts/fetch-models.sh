#!/bin/sh
# Download the Kokoro-82M v1.0 ONNX model and voice pack (about 350 MB) if missing.
set -eu
DIR="${MODELS_DIR:-$(dirname "$0")/../models}"
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
mkdir -p "$DIR"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ ! -s "$DIR/$f" ]; then
    echo "downloading $f"
    curl -fL --retry 3 -o "$DIR/$f.part" "$BASE/$f"
    mv "$DIR/$f.part" "$DIR/$f"
  fi
done
