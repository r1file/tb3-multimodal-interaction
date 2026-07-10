#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${TB3_COMPOSE_DIR:-$(cd "$SCRIPT_DIR/../../../../.." && pwd)}"

cd "$COMPOSE_DIR"
docker compose up -d turtlebot3 tb3_asr tb3_tts

echo "Stopping existing Server dashboard processes..."
set +e
docker exec -i turtlebot3 python3 - <<'PY'
import os
import signal
import subprocess
import time

PATTERNS = (
    'server_dashboard.launch.py',
    'start_server_dashboard.sh',
    'server_control_node',
    'av_recorder_node',
)


def matching_pids():
    protected = {os.getpid(), os.getppid()}
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
        if pid in protected:
            continue
        if any(pattern in args for pattern in PATTERNS):
            pids.append(pid)
    return pids


for sig in (signal.SIGTERM, signal.SIGKILL):
    pids = matching_pids()
    if pids:
        print(f'Sending {sig.name} to Server stack PIDs: {pids}', flush=True)
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
  echo "Warning: Server cleanup exited with status $cleanup_status; continuing startup." >&2
fi

docker exec -d turtlebot3 bash -lc \
  'bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_server_dashboard.sh >/tmp/server_stack.log 2>&1'

for _ in $(seq 1 50); do
  if docker exec turtlebot3 bash -lc 'curl -fsS --max-time 0.5 http://127.0.0.1:8775/status.json >/dev/null' >/dev/null 2>&1; then
    echo "Server dashboard ready: http://127.0.0.1:8775/"
    exit 0
  fi
  sleep 0.2
done

echo "Warning: Server dashboard did not respond within timeout." >&2
exit 1
