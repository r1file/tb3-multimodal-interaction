#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="__TB3_REPO_DIR__"
export TB3_ROLE=tb3
export TB3_HOST_MANIFEST="__TB3_HOST_MANIFEST__"
source "$REPO_ROOT/deploy/lib/load_env.sh"
URL="${1:-http://127.0.0.1:$TB3_UI_PORT}"
START_SCRIPT="$REPO_ROOT/scripts/start_touch_gui_host.sh"

if [[ ! -f "$START_SCRIPT" ]]; then
  echo "Error: canonical TB3 browser launcher not found: $START_SCRIPT" >&2
  exit 1
fi

# The canonical launcher enforces one Epiphany instance and one WebKit page.
exec bash "$START_SCRIPT" "$URL"
