#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8765}"
DISPLAY_VALUE="${DISPLAY:-:0}"
PROFILE_DIR="${TB3_UI_EPIPHANY_PROFILE:-${HOME:-/home/turtlebot3}/.cache/tb3_ui/epiphany-profile}"
EPIPHANY_LOG="${TB3_UI_EPIPHANY_LOG:-${HOME:-/home/turtlebot3}/.cache/tb3_ui/tb3_ui_epiphany.log}"
XORG_LOG="${TB3_UI_XORG_LOG:-/tmp/tb3_ui_xorg.log}"
OPENBOX_LOG="${TB3_UI_OPENBOX_LOG:-/tmp/tb3_ui_openbox.log}"
IDESK_LOG="${TB3_UI_IDESK_LOG:-/tmp/tb3_ui_idesk.log}"
XORG_VT="${TB3_UI_XORG_VT:-vt1}"

wait_for_face_server() {
  for _ in $(seq 1 50); do
    if curl -fsS --max-time 0.5 "${URL%/}/state.json" >/dev/null 2>&1 ||
       curl -fsS --max-time 0.5 "$URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done
  echo "Warning: face server did not respond quickly; opening browser anyway." >&2
}

start_xorg_if_needed() {
  if pgrep -x Xorg >/dev/null 2>&1; then
    return 0
  fi

  if ! command -v Xorg >/dev/null 2>&1; then
    echo "Warning: Xorg command not found." >&2
    return 0
  fi

  if [ "$(id -u)" -eq 0 ]; then
    nohup Xorg :0 "$XORG_VT" -nolisten tcp >"$XORG_LOG" 2>&1 &
  else
    if sudo -n true 2>/dev/null; then
      sudo -n nohup Xorg :0 "$XORG_VT" -nolisten tcp >"$XORG_LOG" 2>&1 &
    elif [ -t 0 ]; then
      echo "Starting Xorg requires sudo. Authenticating before switching the display." >&2
      sudo -v
      sudo -n nohup Xorg :0 "$XORG_VT" -nolisten tcp >"$XORG_LOG" 2>&1 &
    else
      echo "Warning: Xorg is not running and sudo needs a password." >&2
      echo "Run 'sudo -v' first from an interactive TB3 host shell, then rerun this script." >&2
      return 1
    fi
  fi
  sleep 1
}

start_openbox_if_needed() {
  if pgrep -x openbox >/dev/null 2>&1; then
    return 0
  fi

  if command -v openbox >/dev/null 2>&1; then
    DISPLAY="$DISPLAY_VALUE" nohup openbox >"$OPENBOX_LOG" 2>&1 &
    sleep 0.5
  fi
}

start_idesk_if_needed() {
  if ! command -v idesk >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -x idesk >/dev/null 2>&1; then
    return 0
  fi
  DISPLAY="$DISPLAY_VALUE" HOME="${HOME:-/home/turtlebot3}" nohup idesk >"$IDESK_LOG" 2>&1 &
  sleep 0.5
}

wait_for_face_server
start_xorg_if_needed
start_openbox_if_needed
start_idesk_if_needed

pkill -f epiphany || true
pkill -f WebKit || true
pkill -f xdg-dbus-proxy || true
sleep 0.5

mkdir -p "$PROFILE_DIR"
find "$PROFILE_DIR" -type f \( -name "*.lock" -o -name "*-journal" \) -delete 2>/dev/null || true

export DISPLAY="$DISPLAY_VALUE"
export GDK_BACKEND=x11
export GSK_RENDERER=cairo
export GTK_USE_PORTAL=0
export NO_AT_BRIDGE=1
export WEBKIT_DISABLE_COMPOSITING_MODE=1

if command -v dbus-run-session >/dev/null 2>&1; then
  nohup dbus-run-session -- epiphany-browser --new-window --profile="$PROFILE_DIR" "$URL" >"$EPIPHANY_LOG" 2>&1 &
else
  nohup epiphany-browser --new-window --profile="$PROFILE_DIR" "$URL" >"$EPIPHANY_LOG" 2>&1 &
fi

if command -v xdotool >/dev/null 2>&1; then
  (
    sleep 4
    DISPLAY="$DISPLAY_VALUE" xdotool key F11 >/dev/null 2>&1 || true
  ) &
fi

echo "TB3 touch GUI requested at $URL"
echo "Epiphany log: $EPIPHANY_LOG"
