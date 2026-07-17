#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:?MODEL is required from the host manifest}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:?PORT is required from the host manifest}"
CTX_SIZE="${CTX_SIZE:?CTX_SIZE is required from the host manifest}"
GPU_LAYERS="${GPU_LAYERS:?GPU_LAYERS is required from the host manifest}"
ROOT="${ROOT:?ROOT is required from the host manifest}"
WAIT_TIMEOUT_S="${WAIT_TIMEOUT_S:?WAIT_TIMEOUT_S is required from the host manifest}"
LLAMA_SERVER="${LLAMA_SERVER:?LLAMA_SERVER is required from the host manifest}"
MODEL_PATH="${MODEL_PATH:?MODEL_PATH is required from the host manifest}"
MMPROJ_PATH="${MMPROJ_PATH:?MMPROJ_PATH is required from the host manifest}"
RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:?RUNTIME_LOG_RETENTION_DAYS is required from the host manifest}"
RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:?RUNTIME_LOG_RETAIN_FILES is required from the host manifest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_SCRIPT="$SCRIPT_DIR/start_qwen3vl_server.sh"
LOG_DIR="$ROOT/vlm_server_logs"
PID_PATH="$LOG_DIR/llama_server_${MODEL}_${PORT}.pid"
WRAPPER_LOG="$LOG_DIR/restart_qwen3vl_server_${MODEL}_${PORT}_$(date +%Y%m%d_%H%M%S).log"

if [[ ! -x "$START_SCRIPT" && ! -f "$START_SCRIPT" ]]; then
  echo "Missing start script: $START_SCRIPT" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
find "$LOG_DIR" -maxdepth 1 -type f -name '*.log' -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
find "$LOG_DIR" -maxdepth 1 -type f -name '*.log' -print 2>/dev/null \
  | sort -r | tail -n "+$((RETAIN_FILES + 1))" | xargs -r rm -f --

echo "Restarting $MODEL on $HOST:$PORT"
echo "Stopping existing llama-server processes for port $PORT..."

PIDS=()
if command -v lsof >/dev/null 2>&1; then
  while IFS= read -r pid; do
    [[ -n "$pid" ]] && PIDS+=("$pid")
  done < <(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
fi

while IFS= read -r line; do
  pid="${line%% *}"
  [[ -z "$pid" ]] && continue
  if [[ "$line" == *"llama-server"* && "$line" == *"--port $PORT"* ]]; then
    PIDS+=("$pid")
  fi
done < <(pgrep -af llama-server 2>/dev/null || true)

if [[ -f "$PID_PATH" ]]; then
  old_pid="$(cat "$PID_PATH" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    PIDS+=("$old_pid")
  fi
fi

if ((${#PIDS[@]} > 0)); then
  mapfile -t UNIQUE_PIDS < <(printf "%s\n" "${PIDS[@]}" | awk 'NF && !seen[$0]++')
  echo "Found PIDs: ${UNIQUE_PIDS[*]}"
  kill "${UNIQUE_PIDS[@]}" 2>/dev/null || true
  sleep 2
  for pid in "${UNIQUE_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      echo "PID $pid still alive; sending SIGKILL"
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
else
  echo "No existing llama-server process found for port $PORT."
fi

rm -f "$PID_PATH"

echo "Starting fresh service..."
nohup env \
  MODEL="$MODEL" \
  HOST="$HOST" \
  PORT="$PORT" \
  CTX_SIZE="$CTX_SIZE" \
  GPU_LAYERS="$GPU_LAYERS" \
  ROOT="$ROOT" \
  LLAMA_SERVER="$LLAMA_SERVER" \
  MODEL_PATH="$MODEL_PATH" \
  MMPROJ_PATH="$MMPROJ_PATH" \
  bash "$START_SCRIPT" >"$WRAPPER_LOG" 2>&1 &
NEW_PID="$!"
echo "$NEW_PID" > "$PID_PATH"

echo "Wrapper PID: $NEW_PID"
echo "Wrapper log: $WRAPPER_LOG"
echo "PID file: $PID_PATH"

deadline=$((SECONDS + WAIT_TIMEOUT_S))
until curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 || \
      curl -fsS "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; do
  if ! kill -0 "$NEW_PID" 2>/dev/null; then
    echo "Service process exited before becoming ready. Recent log:" >&2
    tail -n 80 "$WRAPPER_LOG" >&2 || true
    exit 1
  fi
  if ((SECONDS >= deadline)); then
    echo "Timed out waiting for llama-server readiness on port $PORT." >&2
    echo "Recent log:" >&2
    tail -n 80 "$WRAPPER_LOG" >&2 || true
    exit 1
  fi
  sleep 2
done

echo "Ready: http://127.0.0.1:$PORT"
