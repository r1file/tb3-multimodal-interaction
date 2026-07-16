#!/usr/bin/env bash
set -uo pipefail

URL="${1:?URL is required}"
PROFILE_DIR="${2:?profile directory is required}"
DISPLAY_VALUE="${3:-:0}"
OPENBOX_UNIT="${4:-tb3-ui-openbox.service}"
browser_pid=""

openbox_ready() {
  systemctl --user is-active --quiet "$OPENBOX_UNIT" &&
    ps -C openbox -o stat= 2>/dev/null | grep -qv '^[[:space:]]*Z'
}

display_ready() {
  DISPLAY="$DISPLAY_VALUE" xset q >/dev/null 2>&1
}

stop_child() {
  if [[ -n "$browser_pid" ]] && kill -0 "$browser_pid" 2>/dev/null; then
    kill -TERM "$browser_pid" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "$browser_pid" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "$browser_pid" 2>/dev/null || true
  fi
  [[ -z "$browser_pid" ]] || wait "$browser_pid" 2>/dev/null || true
}

trap stop_child EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! display_ready; then
  echo "Error: X display $DISPLAY_VALUE is unavailable; refusing to start Epiphany." >&2
  exit 1
fi
if ! openbox_ready; then
  echo "Error: Openbox unit $OPENBOX_UNIT is unavailable; refusing to start Epiphany." >&2
  exit 1
fi

epiphany-browser --profile="$PROFILE_DIR" "$URL" &
browser_pid=$!

while kill -0 "$browser_pid" 2>/dev/null; do
  if ! display_ready; then
    echo "X display $DISPLAY_VALUE disappeared; stopping Epiphany." >&2
    exit 1
  fi
  if ! openbox_ready; then
    echo "Openbox unit $OPENBOX_UNIT stopped; stopping Epiphany." >&2
    exit 1
  fi
  sleep 1
done

wait "$browser_pid"
status=$?
browser_pid=""
exit "$status"
