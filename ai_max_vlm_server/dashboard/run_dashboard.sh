#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-tb3-ai-max-dashboard:latest}"
NAME="${NAME:-tb3-ai-max-dashboard}"
PORT="${PORT:-18181}"
LLAMA_PORT="${LLAMA_PORT:-18082}"
SERVER_STATUS_URL="${SERVER_STATUS_URL:-http://192.168.250.30:8775/status.json}"
ROOT="${ROOT:-/home/user/ROS_Cui}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker build -t "$IMAGE" "$SCRIPT_DIR"

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d \
  --name "$NAME" \
  --restart unless-stopped \
  --pid host \
  --add-host=host.docker.internal:host-gateway \
  -p "$PORT:18181" \
  -e DASHBOARD_PORT=18181 \
  -e LLAMA_BASE_URL="http://host.docker.internal:$LLAMA_PORT" \
  -e SERVER_STATUS_URL="$SERVER_STATUS_URL" \
  -e LLAMA_LOG_DIR=/logs \
  -v "$ROOT/vlm_server_logs:/logs:ro" \
  "$IMAGE"

echo "AI Max dashboard started: http://$(hostname -I | awk '{print $1}'):$PORT/"
echo "Container: $NAME"
