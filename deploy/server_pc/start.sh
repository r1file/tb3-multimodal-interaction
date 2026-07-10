#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"

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
TB3_COMPOSE_DIR="$SERVER_COMPOSE_DIR" bash "$REPO_ROOT/scripts/start_server_stack_host.sh"
VLM_BASE_URL="$VLM_BASE_URL" VLM_MODEL="$VLM_MODEL" \
  bash "$REPO_ROOT/scripts/start_vlm_client_host.sh"

pkill -f "$REPO_ROOT/ai_max_vlm_server/dashboard/server_status_relay.py" >/dev/null 2>&1 || true
nohup env \
  SOURCE_URL=http://127.0.0.1:8775/status.json \
  TARGET_URL="http://$AI_MAX_IP:$VLM_DASHBOARD_PORT/api/server_status" \
  python3 "$REPO_ROOT/ai_max_vlm_server/dashboard/server_status_relay.py" \
  >/tmp/server_status_relay.log 2>&1 &
echo "$!" >/tmp/server_status_relay.pid

echo "Server PC stack ready: http://$SERVER_PC_IP:8775/"
