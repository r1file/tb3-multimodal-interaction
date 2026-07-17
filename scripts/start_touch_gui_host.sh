#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="${1:?TB3 UI URL is required}"
DISPLAY_VALUE="${TB3_DISPLAY:?TB3_DISPLAY is required from the host manifest}"
HOME_VALUE="${TB3_HOME_DIR:?TB3_HOME_DIR is required from the host manifest}"
PROFILE_DIR="${TB3_UI_EPIPHANY_PROFILE:-$HOME_VALUE/.cache/tb3_ui/epiphany-profile}"
EPIPHANY_LOG="${TB3_UI_EPIPHANY_LOG:-$HOME_VALUE/.cache/tb3_ui/tb3_ui_epiphany.log}"
XORG_LOG="${TB3_UI_XORG_LOG:-/tmp/tb3_ui_xorg.log}"
OPENBOX_LOG="${TB3_UI_OPENBOX_LOG:-/tmp/tb3_ui_openbox.log}"
IDESK_LOG="${TB3_UI_IDESK_LOG:-/tmp/tb3_ui_idesk.log}"
XORG_VT="${TB3_UI_XORG_VT:?TB3_UI_XORG_VT is required from the host manifest}"
XORG_READY_TIMEOUT_S="${TB3_UI_XORG_READY_TIMEOUT_S:-20}"
OPENBOX_READY_TIMEOUT_S="${TB3_UI_OPENBOX_READY_TIMEOUT_S:-5}"
BROWSER_READY_TIMEOUT_S="${TB3_UI_BROWSER_READY_TIMEOUT_S:-20}"
XORG_UNIT="${TB3_UI_XORG_UNIT:-tb3-ui-xorg.service}"
OPENBOX_UNIT="${TB3_UI_OPENBOX_UNIT:-tb3-ui-openbox.service}"
IDESK_UNIT="${TB3_UI_IDESK_UNIT:-tb3-ui-idesk.service}"
BROWSER_UNIT="${TB3_UI_BROWSER_UNIT:-tb3-ui-browser.service}"

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

x_display_ready() {
  DISPLAY="$DISPLAY_VALUE" xset q >/dev/null 2>&1
}

wait_for_x_display() {
  local timeout_s="$1"
  local attempts=$((timeout_s * 10))
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if x_display_ready; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

live_named_process() {
  local process_name="$1"
  local state
  while IFS= read -r state; do
    state="${state//[[:space:]]/}"
    if [[ -n "$state" && "${state:0:1}" != "Z" ]]; then
      return 0
    fi
  done < <(ps -C "$process_name" -o stat= 2>/dev/null || true)
  return 1
}

live_xorg_running() {
  live_named_process Xorg
}

start_xorg_if_needed() {
  if x_display_ready; then
    return 0
  fi

  if ! command -v xset >/dev/null 2>&1; then
    echo "Error: xset is required to verify that the X display is ready." >&2
    return 1
  fi

  if ! command -v Xorg >/dev/null 2>&1; then
    echo "Error: Xorg command not found." >&2
    return 1
  fi

  if live_xorg_running; then
    echo "Xorg is running but display $DISPLAY_VALUE is not ready; waiting for it..."
    if wait_for_x_display "$XORG_READY_TIMEOUT_S"; then
      return 0
    fi
    echo "Display is still unavailable; waiting for the stale Xorg process to exit..." >&2
    for _ in $(seq 1 100); do
      if ! live_xorg_running; then
        break
      fi
      sleep 0.1
    done
    if live_xorg_running; then
      echo "Error: Xorg stayed alive but display $DISPLAY_VALUE never became ready." >&2
      tail -n 80 "$XORG_LOG" >&2 2>/dev/null || true
      return 1
    fi
  fi

  mkdir -p "$(dirname "$XORG_LOG")"
  local -a systemd_run=(systemd-run)
  local -a systemctl_cmd=(systemctl)
  if [ "$(id -u)" -ne 0 ]; then
    if sudo -n true 2>/dev/null; then
      systemd_run=(sudo -n systemd-run)
      systemctl_cmd=(sudo -n systemctl)
    elif [ -t 0 ]; then
      echo "Starting Xorg requires sudo. Authenticating before switching the display." >&2
      sudo -v
      systemd_run=(sudo -n systemd-run)
      systemctl_cmd=(sudo -n systemctl)
    else
      echo "Warning: Xorg is not running and sudo needs a password." >&2
      echo "Run 'sudo -v' first from an interactive TB3 host shell, then rerun this script." >&2
      return 1
    fi
  fi

  "${systemctl_cmd[@]}" stop "$XORG_UNIT" >/dev/null 2>&1 || true
  "${systemctl_cmd[@]}" reset-failed "$XORG_UNIT" >/dev/null 2>&1 || true
  "${systemd_run[@]}" \
    --unit="$XORG_UNIT" \
    --collect \
    --property=Restart=on-failure \
    --property=RestartSec=1s \
    --property="StandardOutput=append:$XORG_LOG" \
    --property="StandardError=append:$XORG_LOG" \
    -- Xorg "$DISPLAY_VALUE" "$XORG_VT" -nolisten tcp >/dev/null

  if ! wait_for_x_display "$XORG_READY_TIMEOUT_S"; then
    echo "Error: display $DISPLAY_VALUE was not ready after ${XORG_READY_TIMEOUT_S}s." >&2
    tail -n 80 "$XORG_LOG" >&2 2>/dev/null || true
    return 1
  fi
  echo "X display ready: $DISPLAY_VALUE"
}

start_openbox_if_needed() {
  if systemctl --user is-active --quiet "$OPENBOX_UNIT" && live_named_process openbox; then
    return 0
  fi

  if command -v openbox >/dev/null 2>&1; then
    mkdir -p "$(dirname "$OPENBOX_LOG")"
    systemctl --user stop "$OPENBOX_UNIT" >/dev/null 2>&1 || true
    systemctl --user reset-failed "$OPENBOX_UNIT" >/dev/null 2>&1 || true
    pkill -x openbox 2>/dev/null || true
    systemd-run --user \
      --unit="$OPENBOX_UNIT" \
      --collect \
      --property=Restart=on-failure \
      --property=RestartSec=1s \
      --property="StandardOutput=append:$OPENBOX_LOG" \
      --property="StandardError=append:$OPENBOX_LOG" \
      --setenv="DISPLAY=$DISPLAY_VALUE" \
      --setenv="HOME=$HOME_VALUE" \
      -- openbox >/dev/null
    for ((attempt = 0; attempt < OPENBOX_READY_TIMEOUT_S * 10; attempt++)); do
      if systemctl --user is-active --quiet "$OPENBOX_UNIT" && live_named_process openbox; then
        echo "Openbox ready on $DISPLAY_VALUE"
        return 0
      fi
      sleep 0.1
    done
    echo "Error: Openbox failed to stay running on $DISPLAY_VALUE." >&2
    tail -n 80 "$OPENBOX_LOG" >&2 2>/dev/null || true
    return 1
  fi

  echo "Error: openbox command not found." >&2
  return 1
}

start_idesk_if_needed() {
  if ! command -v idesk >/dev/null 2>&1; then
    return 0
  fi
  if systemctl --user is-active --quiet "$IDESK_UNIT" && live_named_process idesk; then
    return 0
  fi
  mkdir -p "$(dirname "$IDESK_LOG")"
  systemctl --user stop "$IDESK_UNIT" >/dev/null 2>&1 || true
  systemctl --user reset-failed "$IDESK_UNIT" >/dev/null 2>&1 || true
  pkill -x idesk 2>/dev/null || true
  systemd-run --user \
    --unit="$IDESK_UNIT" \
    --collect \
    --property=Restart=on-failure \
    --property=RestartSec=1s \
    --property="StandardOutput=append:$IDESK_LOG" \
    --property="StandardError=append:$IDESK_LOG" \
    --setenv="DISPLAY=$DISPLAY_VALUE" \
    --setenv="HOME=$HOME_VALUE" \
    -- idesk >/dev/null
  sleep 0.5
}

stop_browser() {
  systemctl --user stop "$BROWSER_UNIT" >/dev/null 2>&1 || true
  systemctl --user reset-failed "$BROWSER_UNIT" >/dev/null 2>&1 || true

  if live_named_process epiphany ||
     pgrep -f '^/usr/lib/.*/WebKit(Network|Web)Process( |$)' >/dev/null 2>&1; then
    echo "Stopping existing Epiphany/WebKit processes before browser startup..."
  fi
  pkill -x epiphany 2>/dev/null || true
  pkill -f '^/usr/lib/.*/WebKit(Network|Web)Process( |$)' 2>/dev/null || true
  pkill -x xdg-dbus-proxy 2>/dev/null || true
  pkill -f '^dbus-run-session -- epiphany-browser( |$)' 2>/dev/null || true
  for _ in $(seq 1 50); do
    if ! live_named_process epiphany &&
       ! pgrep -f '^/usr/lib/.*/WebKit(Network|Web)Process( |$)' >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done
  echo "Error: previous Epiphany/WebKit processes did not stop." >&2
  return 1
}

clear_browser_session() {
  mkdir -p "$PROFILE_DIR"
  # Epiphany restores every window recorded here. Retaining these files while
  # also passing a URL creates another UI window on every stack restart.
  find "$PROFILE_DIR" -maxdepth 1 -type f \
    \( -name 'session_state.xml' -o -name 'session_state.xml~' -o -name '.goutputstream-*' \) \
    -delete 2>/dev/null || true
  find "$PROFILE_DIR" -type f \( -name '*.lock' -o -name '*-journal' \) \
    -delete 2>/dev/null || true
}

browser_process_count() {
  pgrep -cx epiphany 2>/dev/null || true
}

webkit_page_count() {
  pgrep -fc '^/usr/lib/.*/WebKitWebProcess( |$)' 2>/dev/null || true
}

browser_ready() {
  x_display_ready &&
    systemctl --user is-active --quiet "$OPENBOX_UNIT" &&
    live_named_process openbox &&
    systemctl --user is-active --quiet "$BROWSER_UNIT" &&
    [[ "$(browser_process_count)" -eq 1 ]] &&
    [[ "$(webkit_page_count)" -eq 1 ]]
}

wait_for_browser() {
  local attempt
  local attempts=$((BROWSER_READY_TIMEOUT_S * 10))
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if browser_ready; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

launch_browser() {
  local -a browser_command=(
    "$SCRIPT_DIR/run_epiphany_guarded.sh"
    "$URL"
    "$PROFILE_DIR"
    "$DISPLAY_VALUE"
    "$OPENBOX_UNIT"
  )
  if command -v dbus-run-session >/dev/null 2>&1; then
    browser_command=(dbus-run-session -- "${browser_command[@]}")
  fi
  systemd-run --user \
    --unit="$BROWSER_UNIT" \
    --collect \
    --property="BindsTo=$OPENBOX_UNIT" \
    --property="After=$OPENBOX_UNIT" \
    --property=Restart=no \
    --property=TimeoutStopSec=5s \
    --property="StandardOutput=append:$EPIPHANY_LOG" \
    --property="StandardError=append:$EPIPHANY_LOG" \
    --setenv="DISPLAY=$DISPLAY_VALUE" \
    --setenv="HOME=$HOME_VALUE" \
    --setenv="XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    --setenv=GDK_BACKEND=x11 \
    --setenv=GSK_RENDERER=cairo \
    --setenv=GTK_USE_PORTAL=0 \
    --setenv=NO_AT_BRIDGE=1 \
    --setenv=WEBKIT_DISABLE_COMPOSITING_MODE=1 \
    -- "${browser_command[@]}" >/dev/null
}

wait_for_face_server
start_xorg_if_needed
start_openbox_if_needed
start_idesk_if_needed

stop_browser

mkdir -p "$PROFILE_DIR"
mkdir -p "$(dirname "$EPIPHANY_LOG")"
clear_browser_session
: >"$EPIPHANY_LOG"

export DISPLAY="$DISPLAY_VALUE"
export GDK_BACKEND=x11
export GSK_RENDERER=cairo
export GTK_USE_PORTAL=0
export NO_AT_BRIDGE=1
export WEBKIT_DISABLE_COMPOSITING_MODE=1

browser_started=0
for attempt in 1 2; do
  echo "Starting Epiphany (attempt $attempt/2)..." >>"$EPIPHANY_LOG"
  launch_browser
  if wait_for_browser; then
    browser_started=1
    break
  fi
  echo "Epiphany attempt $attempt did not become ready within ${BROWSER_READY_TIMEOUT_S}s." >>"$EPIPHANY_LOG"
  stop_browser || true
  sleep 1
done

if [[ "$browser_started" -ne 1 ]]; then
  echo "Error: Epiphany failed to create exactly one WebKit page after two attempts." >&2
  tail -n 120 "$EPIPHANY_LOG" >&2 2>/dev/null || true
  exit 1
fi

if command -v xdotool >/dev/null 2>&1; then
  (
    sleep 4
    DISPLAY="$DISPLAY_VALUE" xdotool key F11 >/dev/null 2>&1 || true
  ) &
fi

echo "TB3 touch GUI ready at $URL"
echo "Browser single-instance check: epiphany=$(browser_process_count) webkit_pages=$(webkit_page_count)"
echo "Epiphany log: $EPIPHANY_LOG"
