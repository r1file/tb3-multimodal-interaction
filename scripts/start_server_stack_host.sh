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

for _ in $(seq 1 50); do
  if docker exec "$CONTAINER" bash -lc "curl -fsS --max-time 0.5 http://127.0.0.1:$SERVER_DASHBOARD_PORT/status.json >/dev/null" >/dev/null 2>&1; then
    echo "Server dashboard ready: http://127.0.0.1:$SERVER_DASHBOARD_PORT/"
    exit 0
  fi
  sleep 0.2
done

echo "Warning: Server dashboard did not respond within timeout." >&2
echo "Log: $RUNTIME_LOG_DIR/server_stack.log inside $CONTAINER" >&2
exit 1
