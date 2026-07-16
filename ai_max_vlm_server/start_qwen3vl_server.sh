#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-qwen3vl8b}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-18082}"
CTX_SIZE="${CTX_SIZE:-4096}"
GPU_LAYERS="${GPU_LAYERS:-999}"
ROOT="${ROOT:-/home/user/ROS_Cui}"
LLAMA_SERVER="${LLAMA_SERVER:-$ROOT/llama.cpp/build/bin/llama-server}"
MODEL_PATH="${MODEL_PATH:-}"
MMPROJ_PATH="${MMPROJ_PATH:-}"

case "$MODEL" in
  qwen3vl2b)
    MODEL_PATH="${MODEL_PATH:-/home/user/.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct-GGUF/snapshots/52d6c8ffea26cc873ac5ad116f8631268d7eb503/Qwen3VL-2B-Instruct-Q4_K_M.gguf}"
    MMPROJ_PATH="${MMPROJ_PATH:-/home/user/.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct-GGUF/snapshots/52d6c8ffea26cc873ac5ad116f8631268d7eb503/mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf}"
    ;;
  qwen3vl8b)
    MODEL_PATH="${MODEL_PATH:-/home/user/.cache/huggingface/hub/models--Qwen--Qwen3-VL-8B-Instruct-GGUF/snapshots/f982a07559d4a2f6c8744d840bf6fccab30eea96/Qwen3VL-8B-Instruct-Q4_K_M.gguf}"
    MMPROJ_PATH="${MMPROJ_PATH:-/home/user/.cache/huggingface/hub/models--Qwen--Qwen3-VL-8B-Instruct-GGUF/snapshots/f982a07559d4a2f6c8744d840bf6fccab30eea96/mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf}"
    ;;
  *)
    echo "Unknown MODEL: $MODEL" >&2
    echo "Use MODEL=qwen3vl2b or MODEL=qwen3vl8b" >&2
    exit 2
    ;;
esac

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
