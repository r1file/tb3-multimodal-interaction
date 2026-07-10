#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="${1:-http://127.0.0.1:8765}"

if ! docker ps --format '{{.Names}}' | grep -qx turtlebot3; then
  echo "Error: turtlebot3 container is not running." >&2
  echo "Start it first: cd ~/turtlebot3/docker/jazzy && ./container.sh start" >&2
  exit 1
fi

echo "Stopping existing TB3 device-stack processes..."
set +e
docker exec -i turtlebot3 python3 - <<'PY'
import os
import signal
import subprocess
import time

PATTERNS = (
    'device_stack.launch.py',
    'start_device_stack.sh',
    'motion_controller_node',
    'expression_behavior_node',
    'face_display_node',
    'camera_capture_node',
    'mic_capture_node',
    'speech_player_node',
)


def matching_pids():
    protected_pids = {os.getpid(), os.getppid()}
    output = subprocess.check_output(['ps', '-eo', 'pid,args'], text=True)
    pids = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        pid_text, _, args = line.partition(' ')
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid in protected_pids:
            continue
        if any(pattern in args for pattern in PATTERNS):
            pids.append(pid)
    return pids


for sig in (signal.SIGTERM, signal.SIGKILL):
    pids = matching_pids()
    if pids:
        print(f'Sending {sig.name} to device-stack PIDs: {pids}', flush=True)
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
    time.sleep(1.0)
PY
cleanup_status=$?
set -e
if [ "$cleanup_status" -ne 0 ]; then
  echo "Warning: device-stack cleanup exited with status $cleanup_status; continuing startup." >&2
fi

sleep 0.5

if ! docker exec turtlebot3 bash -lc '
    if grep -Eq "turtlebot3_node.*Run!|diff_drive_controller.*Run!" /tmp/tb3_bringup.log 2>/dev/null; then
      echo "TB3 bringup log Run! found."
      exit 0
    fi
    echo "TB3 bringup log Run! not found; checking ROS topics instead..."
    bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/wait_tb3_bringup_ready.sh 8
  '; then
  echo "Error: TB3 bringup Run! was not found." >&2
  echo "Start TB3 bringup first, then rerun this script." >&2
  echo "Preferred command:" >&2
  echo "  docker exec -d turtlebot3 bash -lc 'bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_tb3_bringup.sh >/tmp/tb3_bringup.log 2>&1'" >&2
  echo "If bringup was started manually, make sure /cmd_vel has a subscriber and /odom has a publisher." >&2
  exit 1
fi

echo "TB3 bringup Run! found; starting device/UI layer."

docker exec -d turtlebot3 bash -lc \
  'bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_device_stack.sh >/tmp/device_stack.log 2>&1'

echo "Waiting for TB3 device-stack health..."
if ! docker exec turtlebot3 bash -lc '
    for _ in $(seq 1 20); do
      bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/health_check_full.sh tb3 && exit 0
      sleep 0.5
    done
    exit 1
  '; then
  echo "Error: TB3 device-stack health check failed." >&2
  echo "Executor log: /tmp/device_stack.log inside the turtlebot3 container" >&2
  exit 1
fi

exec "$SCRIPT_DIR/start_touch_gui_host.sh" "$URL"
