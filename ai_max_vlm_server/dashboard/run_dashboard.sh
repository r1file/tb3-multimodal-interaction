#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:?IMAGE is required from the host manifest}"
NAME="${NAME:?NAME is required from the host manifest}"
PORT="${PORT:?PORT is required from the host manifest}"
LLAMA_PORT="${LLAMA_PORT:?LLAMA_PORT is required from the host manifest}"
SERVER_STATUS_URL="${SERVER_STATUS_URL:?SERVER_STATUS_URL is required from the host manifest}"
ROOT="${ROOT:?ROOT is required from the host manifest}"
STARTUP_GRACE_S="${STARTUP_GRACE_S:?STARTUP_GRACE_S is required from the host manifest}"
STALE_AFTER_S="${STALE_AFTER_S:?STALE_AFTER_S is required from the host manifest}"
BASE_IMAGE="${AI_DASHBOARD_BASE_IMAGE:?AI_DASHBOARD_BASE_IMAGE is required from the host manifest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker build --build-arg PYTHON_BASE_IMAGE="$BASE_IMAGE" -t "$IMAGE" "$SCRIPT_DIR"

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d \
  --name "$NAME" \
  --restart unless-stopped \
  --pid host \
  --add-host=host.docker.internal:host-gateway \
  -p "$PORT:$PORT" \
  -e DASHBOARD_PORT="$PORT" \
  -e LLAMA_BASE_URL="http://host.docker.internal:$LLAMA_PORT" \
  -e SERVER_STATUS_URL="$SERVER_STATUS_URL" \
  -e LLAMA_LOG_DIR=/logs \
  -e STARTUP_GRACE_S="$STARTUP_GRACE_S" \
  -e STALE_AFTER_S="$STALE_AFTER_S" \
  -v "$ROOT/vlm_server_logs:/logs:ro" \
  "$IMAGE"

echo "AI Max dashboard started: http://$(hostname -I | awk '{print $1}'):$PORT/"
echo "Container: $NAME"
