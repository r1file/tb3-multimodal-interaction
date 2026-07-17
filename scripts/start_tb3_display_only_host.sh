#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export TB3_ROLE=tb3
source "$REPO_ROOT/deploy/lib/load_env.sh"
URL="${1:-http://127.0.0.1:$TB3_UI_PORT}"
FACE_LOG="${TB3_UI_FACE_LOG:-/tmp/tb3_face_display.log}"
FACE_START_SCRIPT="/workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_face_gui.sh"

face_server_ready() {
  curl -fsS --max-time 1 "${URL%/}/state.json" >/dev/null 2>&1 ||
    curl -fsS --max-time 1 "$URL" >/dev/null 2>&1
}

if ! docker ps --format '{{.Names}}' | grep -qx "$ROS_CONTAINER"; then
  echo "Error: $ROS_CONTAINER container is not running." >&2
  echo "Start it first with: bash deploy/role.sh tb3 start --manifest $TB3_HOST_MANIFEST" >&2
  exit 1
fi

if face_server_ready; then
  echo "TB3 face UI is already available at $URL"
else
  echo "Starting display-only face server in $ROS_CONTAINER..."
  docker exec "$ROS_CONTAINER" bash -lc \
    "test -x '$FACE_START_SCRIPT' || test -f '$FACE_START_SCRIPT'"

  # Remove a stale face process only when its HTTP endpoint is unavailable.
  docker exec "$ROS_CONTAINER" bash -lc \
    "pkill -f '[f]ace_display_node' >/dev/null 2>&1 || true"
  docker exec -d "$ROS_CONTAINER" bash -lc \
    'exec bash "$1" >"$2" 2>&1' _ "$FACE_START_SCRIPT" "$FACE_LOG"

  for _ in $(seq 1 30); do
    if face_server_ready; then
      break
    fi
    sleep 0.2
  done

  if ! face_server_ready; then
    echo "Error: TB3 face UI did not become available at $URL" >&2
    echo "Container log: $FACE_LOG" >&2
    exit 1
  fi
  echo "TB3 face UI ready at $URL"
fi

exec "$SCRIPT_DIR/start_touch_gui_host.sh" "$URL"
