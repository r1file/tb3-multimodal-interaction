#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"
source "$SCRIPT_DIR/../lib/runtime.sh"

mkdir -p "$AI_MAX_RUNTIME_LOG_DIR"
prune_runtime_logs "$AI_MAX_RUNTIME_LOG_DIR"
write_role_state ai_max starting "starting model and dashboard"
trap 'write_role_state ai_max failed "start failed at line $LINENO"' ERR

MODEL="$VLM_MODEL" \
PORT="$VLM_PORT" \
CTX_SIZE="$VLM_CONTEXT_SIZE" \
GPU_LAYERS="$VLM_GPU_LAYERS" \
WAIT_TIMEOUT_S="$VLM_WAIT_TIMEOUT_S" \
ROOT="$AI_MAX_ROOT" \
LLAMA_SERVER="$LLAMA_SERVER" \
MODEL_PATH="$VLM_MODEL_PATH" \
MMPROJ_PATH="$VLM_MMPROJ_PATH" \
RUNTIME_LOG_RETENTION_DAYS="$RUNTIME_LOG_RETENTION_DAYS" \
RUNTIME_LOG_RETAIN_FILES="$RUNTIME_LOG_RETAIN_FILES" \
  bash "$REPO_ROOT/ai_max_vlm_server/restart_qwen3vl_server.sh"

PORT="$VLM_DASHBOARD_PORT" \
LLAMA_PORT="$VLM_PORT" \
ROOT="$AI_MAX_ROOT" \
SERVER_STATUS_URL="http://$SERVER_PC_IP:$SERVER_DASHBOARD_PORT/status.json" \
  bash "$REPO_ROOT/ai_max_vlm_server/dashboard/run_dashboard.sh"

dashboard_ready=0
for _ in $(seq 1 20); do
  if curl -fsS --max-time 5 \
    "http://127.0.0.1:$VLM_DASHBOARD_PORT/api/status" >/dev/null 2>&1; then
    dashboard_ready=1
    break
  fi
  sleep 0.25
done
if [[ "$dashboard_ready" -ne 1 ]]; then
  echo "AI Max dashboard API did not become ready on port $VLM_DASHBOARD_PORT." >&2
  docker logs --tail 100 tb3-ai-max-dashboard >&2 || true
  exit 1
fi

write_role_state ai_max ready "model and dashboard ready"
trap - ERR

echo "AI Max VLM ready: http://$AI_MAX_IP:$VLM_PORT/"
echo "AI Max dashboard: http://$AI_MAX_IP:$VLM_DASHBOARD_PORT/"
