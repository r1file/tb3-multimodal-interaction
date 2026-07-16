#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${TB3_COMPOSE_DIR:-$(cd "$SCRIPT_DIR/../../../../.." && pwd)}"
SERVER_DASHBOARD_PORT="${SERVER_DASHBOARD_PORT:-8775}"
TB3_IP="${TB3_IP:-192.168.250.10}"
TB3_UI_PORT="${TB3_UI_PORT:-8765}"
RUNTIME_LOG_DIR="${CONTAINER_RUNTIME_LOG_DIR:-/workspace/runtime_logs/tb3_multimodal_interaction}"
RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:-14}"
RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:-20}"

cd "$COMPOSE_DIR"
docker compose up -d turtlebot3 tb3_asr tb3_tts

echo "Stopping existing Server dashboard processes..."
docker exec turtlebot3 python3 \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/stop_matching_processes.py \
  server_dashboard.launch.py start_server_dashboard.sh server_control_node av_recorder_node evaluation_logger_node
docker exec turtlebot3 bash \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/prepare_runtime_log.sh \
  "$RUNTIME_LOG_DIR/server_stack.log" "$RETENTION_DAYS" "$RETAIN_FILES"

docker exec -d \
  -e SERVER_DASHBOARD_PORT="$SERVER_DASHBOARD_PORT" \
  -e TB3_IP="$TB3_IP" \
  -e TB3_UI_PORT="$TB3_UI_PORT" \
  turtlebot3 bash -lc \
  "bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_server_dashboard.sh >'$RUNTIME_LOG_DIR/server_stack.log' 2>&1"

for _ in $(seq 1 50); do
  if docker exec turtlebot3 bash -lc "curl -fsS --max-time 0.5 http://127.0.0.1:$SERVER_DASHBOARD_PORT/status.json >/dev/null" >/dev/null 2>&1; then
    echo "Server dashboard ready: http://127.0.0.1:$SERVER_DASHBOARD_PORT/"
    exit 0
  fi
  sleep 0.2
done

echo "Warning: Server dashboard did not respond within timeout." >&2
echo "Log: $RUNTIME_LOG_DIR/server_stack.log inside turtlebot3" >&2
exit 1
