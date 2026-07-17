#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${SERVER_COMPOSE_DIR:?SERVER_COMPOSE_DIR is required from the host manifest}"
CONTAINER="${ROS_CONTAINER:?ROS_CONTAINER is required from the host manifest}"
SERVER_DASHBOARD_PORT="${SERVER_DASHBOARD_PORT:?SERVER_DASHBOARD_PORT is required from the host manifest}"
TB3_IP="${TB3_IP:?TB3_IP is required from the host manifest}"
TB3_UI_PORT="${TB3_UI_PORT:?TB3_UI_PORT is required from the host manifest}"
RUNTIME_LOG_DIR="${CONTAINER_RUNTIME_LOG_DIR:?CONTAINER_RUNTIME_LOG_DIR is required from the host manifest}"
RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:?RUNTIME_LOG_RETENTION_DAYS is required from the host manifest}"
RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:?RUNTIME_LOG_RETAIN_FILES is required from the host manifest}"
ASR_CONTAINER="${ASR_CONTAINER:?ASR_CONTAINER is required from the host manifest}"
TTS_CONTAINER="${TTS_CONTAINER:?TTS_CONTAINER is required from the host manifest}"
STARTUP_GRACE_S="${ROLE_STARTUP_GRACE_S:?ROLE_STARTUP_GRACE_S is required from the host manifest}"

wait_for_speech_model() {
  local container="$1"
  local label="$2"
  local deadline=$((SECONDS + STARTUP_GRACE_S))

  while ((SECONDS < deadline)); do
    if docker exec "$container" bash -lc \
      'test -s "${SPEECH_MODEL_READY_FILE:?SPEECH_MODEL_READY_FILE is required}"' \
      >/dev/null 2>&1; then
      echo "$label models preloaded in $container"
      return 0
    fi
    if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
      break
    fi
    sleep 0.5
  done

  echo "Error: $label model preload did not finish within ${STARTUP_GRACE_S}s." >&2
  docker logs --tail 120 "$container" >&2 2>/dev/null || true
  return 1
}

cd "$COMPOSE_DIR"
docker compose up -d turtlebot3 tb3_asr tb3_tts

echo "Stopping existing Server dashboard processes..."
docker exec "$CONTAINER" python3 \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/stop_matching_processes.py \
  server_dashboard.launch.py start_server_dashboard.sh server_control_node av_recorder_node evaluation_logger_node
docker exec "$CONTAINER" bash \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/prepare_runtime_log.sh \
  "$RUNTIME_LOG_DIR/server_stack.log" "$RETENTION_DAYS" "$RETAIN_FILES"

docker exec -d \
  -e SERVER_DASHBOARD_PORT="$SERVER_DASHBOARD_PORT" \
  -e TB3_IP="$TB3_IP" \
  -e TB3_UI_PORT="$TB3_UI_PORT" \
  "$CONTAINER" bash -lc \
  "bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_server_dashboard.sh >'$RUNTIME_LOG_DIR/server_stack.log' 2>&1"

dashboard_ready=0
for _ in $(seq 1 50); do
  if docker exec "$CONTAINER" bash -lc "curl -fsS --max-time 0.5 http://127.0.0.1:$SERVER_DASHBOARD_PORT/status.json >/dev/null" >/dev/null 2>&1; then
    dashboard_ready=1
    break
  fi
  sleep 0.2
done

if [[ "$dashboard_ready" -ne 1 ]]; then
  echo "Warning: Server dashboard did not respond within timeout." >&2
  echo "Log: $RUNTIME_LOG_DIR/server_stack.log inside $CONTAINER" >&2
  exit 1
fi

wait_for_speech_model "$ASR_CONTAINER" "ASR"
wait_for_speech_model "$TTS_CONTAINER" "TTS ja/zh/en"
echo "Server dashboard ready: http://127.0.0.1:$SERVER_DASHBOARD_PORT/"
