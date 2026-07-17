#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TB3_ROLE="${TB3_ROLE:-ai_max}"
source "$SCRIPT_DIR/../lib/load_env.sh"

test -x "$LLAMA_SERVER" || { echo "Missing executable: $LLAMA_SERVER" >&2; exit 1; }
command -v docker >/dev/null
command -v curl >/dev/null
mkdir -p "$AI_MAX_RUNTIME_LOG_DIR" "$AI_MAX_ROOT/vlm_server_logs"
echo "AI Max prerequisites present; no external model or llama.cpp asset was modified."
