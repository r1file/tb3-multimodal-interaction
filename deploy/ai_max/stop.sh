#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TB3_ROLE="${TB3_ROLE:-ai_max}"
source "$SCRIPT_DIR/../lib/load_env.sh"
source "$SCRIPT_DIR/../lib/runtime.sh"

write_role_state ai_max stopping "stopping role-owned model and dashboard"
docker rm -f "$AI_DASHBOARD_CONTAINER" >/dev/null 2>&1 || true
python3 "$REPO_ROOT/scripts/stop_matching_processes.py" llama-server start_qwen3vl_server.sh || true
rm -f "$AI_MAX_ROOT/vlm_server_logs/llama_server_${VLM_MODEL}_${VLM_PORT}.pid"
write_role_state ai_max stopped "role-owned services stopped"
echo "AI Max stopped; Docker daemon, logs, models, and backups were retained."
