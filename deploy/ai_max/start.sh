#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"

MODEL="$VLM_MODEL" \
PORT="$VLM_PORT" \
CTX_SIZE="$VLM_CONTEXT_SIZE" \
GPU_LAYERS="$VLM_GPU_LAYERS" \
WAIT_TIMEOUT_S="$VLM_WAIT_TIMEOUT_S" \
ROOT="$AI_MAX_ROOT" \
  bash "$REPO_ROOT/ai_max_vlm_server/restart_qwen3vl_server.sh"

PORT="$VLM_DASHBOARD_PORT" \
LLAMA_PORT="$VLM_PORT" \
ROOT="$AI_MAX_ROOT" \
SERVER_STATUS_URL="http://$SERVER_PC_IP:8775/status.json" \
  bash "$REPO_ROOT/ai_max_vlm_server/dashboard/run_dashboard.sh"

echo "AI Max VLM ready: http://$AI_MAX_IP:$VLM_PORT/"
echo "AI Max dashboard: http://$AI_MAX_IP:$VLM_DASHBOARD_PORT/"
