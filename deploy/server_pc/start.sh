#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"
source "$SCRIPT_DIR/../lib/runtime.sh"

mkdir -p "$SERVER_RUNTIME_LOG_DIR"
prune_runtime_logs "$SERVER_RUNTIME_LOG_DIR"
write_role_state server_pc starting "starting ROS, ASR, TTS, dashboard, VLM client, and relay"
trap 'write_role_state server_pc failed "start failed at line $LINENO"' ERR

cd "$SERVER_COMPOSE_DIR"
docker compose up -d "$ROS_CONTAINER"

docker exec "$ROS_CONTAINER" bash -lc "
set -e
source /opt/ros/jazzy/setup.bash
cd /workspace/ros2_ws
colcon build --packages-select tb3_multimodal_interaction --symlink-install
"

for legacy_container in week3_asr week3_tts; do
  docker rm -f "$legacy_container" >/dev/null 2>&1 || true
done

docker compose up -d tb3_asr tb3_tts
TB3_COMPOSE_DIR="$SERVER_COMPOSE_DIR" \
  CONTAINER_RUNTIME_LOG_DIR="$CONTAINER_RUNTIME_LOG_DIR" \
  RUNTIME_LOG_RETENTION_DAYS="$RUNTIME_LOG_RETENTION_DAYS" \
  RUNTIME_LOG_RETAIN_FILES="$RUNTIME_LOG_RETAIN_FILES" \
  bash "$REPO_ROOT/scripts/start_server_stack_host.sh"
VLM_BASE_URL="$VLM_BASE_URL" VLM_MODEL="$VLM_MODEL" \
  CONTAINER_RUNTIME_LOG_DIR="$CONTAINER_RUNTIME_LOG_DIR" \
  RUNTIME_LOG_RETENTION_DAYS="$RUNTIME_LOG_RETENTION_DAYS" \
  RUNTIME_LOG_RETAIN_FILES="$RUNTIME_LOG_RETAIN_FILES" \
  bash "$REPO_ROOT/scripts/start_vlm_client_host.sh"

python3 "$REPO_ROOT/scripts/stop_matching_processes.py" server_status_relay.py || true
bash "$REPO_ROOT/scripts/prepare_runtime_log.sh" \
  "$SERVER_RUNTIME_LOG_DIR/server_status_relay.log" \
  "$RUNTIME_LOG_RETENTION_DAYS" "$RUNTIME_LOG_RETAIN_FILES"
nohup env \
  SOURCE_URL="http://127.0.0.1:$SERVER_DASHBOARD_PORT/status.json" \
  TARGET_URL="http://$AI_MAX_IP:$VLM_DASHBOARD_PORT/api/server_status" \
  python3 "$REPO_ROOT/ai_max_vlm_server/dashboard/server_status_relay.py" \
  >"$SERVER_RUNTIME_LOG_DIR/server_status_relay.log" 2>&1 &
echo "$!" >"$SERVER_RUNTIME_LOG_DIR/server_status_relay.pid"

sleep 1
kill -0 "$(cat "$SERVER_RUNTIME_LOG_DIR/server_status_relay.pid")"
write_role_state server_pc ready "role stack and status relay ready"
trap - ERR

echo "Server PC stack ready: http://$SERVER_PC_IP:$SERVER_DASHBOARD_PORT/"
