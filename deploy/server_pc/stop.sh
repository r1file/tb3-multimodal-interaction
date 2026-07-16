#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"
source "$SCRIPT_DIR/../lib/runtime.sh"

write_role_state server_pc stopping "stopping role-owned relay and containers"
python3 "$REPO_ROOT/scripts/stop_matching_processes.py" server_status_relay.py || true
rm -f "$SERVER_RUNTIME_LOG_DIR/server_status_relay.pid"
cd "$SERVER_COMPOSE_DIR"
docker compose stop tb3_asr tb3_tts "$ROS_CONTAINER"
write_role_state server_pc stopped "role-owned services stopped"
echo "Server PC stopped; Docker daemon, workspace, logs, models, and backups were retained."
