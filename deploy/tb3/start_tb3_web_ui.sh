#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8765}"
REPO_ROOT="${TB3_REPO_ROOT:-/home/turtlebot3/turtlebot3/docker/jazzy/workspace/ros2_ws/src/tb3_multimodal_interaction}"
START_SCRIPT="$REPO_ROOT/scripts/start_touch_gui_host.sh"

if [[ ! -f "$START_SCRIPT" ]]; then
  echo "Error: canonical TB3 browser launcher not found: $START_SCRIPT" >&2
  exit 1
fi

# The canonical launcher enforces one Epiphany instance and one WebKit page.
exec bash "$START_SCRIPT" "$URL"
