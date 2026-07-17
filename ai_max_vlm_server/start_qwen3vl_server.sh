#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:?MODEL is required from the host manifest}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:?PORT is required from the host manifest}"
CTX_SIZE="${CTX_SIZE:?CTX_SIZE is required from the host manifest}"
GPU_LAYERS="${GPU_LAYERS:?GPU_LAYERS is required from the host manifest}"
ROOT="${ROOT:?ROOT is required from the host manifest}"
LLAMA_SERVER="${LLAMA_SERVER:?LLAMA_SERVER is required from the host manifest}"
MODEL_PATH="${MODEL_PATH:?MODEL_PATH is required from the host manifest}"
MMPROJ_PATH="${MMPROJ_PATH:?MMPROJ_PATH is required from the host manifest}"

for path in "$LLAMA_SERVER" "$MODEL_PATH" "$MMPROJ_PATH"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required path: $path" >&2
    exit 1
  fi
done

mkdir -p "$ROOT/vlm_server_logs"
LOG_PATH="$ROOT/vlm_server_logs/llama_server_${MODEL}_${PORT}_$(date +%Y%m%d_%H%M%S).log"

echo "Starting $MODEL on $HOST:$PORT"
echo "Log: $LOG_PATH"
exec "$LLAMA_SERVER" \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CTX_SIZE" \
  --gpu-layers "$GPU_LAYERS" \
  --model "$MODEL_PATH" \
  --mmproj "$MMPROJ_PATH" \
  2>&1 | tee "$LOG_PATH"
