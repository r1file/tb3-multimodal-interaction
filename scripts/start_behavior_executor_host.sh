#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-turtlebot3}"
DRY_RUN="${TB3_BEHAVIOR_DRY_RUN:-false}"
LOG_PATH="${LOG_PATH:-/tmp/behavior_executor.log}"
PID_PATH="${PID_PATH:-/tmp/behavior_executor.pid}"

docker exec "$CONTAINER" bash -lc "
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
set -u
if [ -s '$PID_PATH' ]; then
  old_pid=\$(cat '$PID_PATH' || true)
  if [ -n \"\$old_pid\" ]; then
    kill \"\$old_pid\" >/dev/null 2>&1 || true
    sleep 0.5
  fi
fi
ps -eo pid,args | awk '/behavior_executor_node/ && !/bash -lc/ && !/awk/ {print \$1}' | xargs -r kill >/dev/null 2>&1 || true
sleep 0.5
nohup ros2 run tb3_multimodal_interaction behavior_executor_node --ros-args \
  -p dry_run:='$DRY_RUN' \
  >'$LOG_PATH' 2>&1 </dev/null &
echo \$! >'$PID_PATH'
sleep 1
if ! kill -0 \$(cat '$PID_PATH') >/dev/null 2>&1; then
  echo 'Behavior executor failed to stay running' >&2
  tail -n 80 '$LOG_PATH' >&2 || true
  exit 1
fi
ps -p \$(cat '$PID_PATH') -o pid=,cmd=
"

echo "Behavior executor started in $CONTAINER"
echo "dry_run=$DRY_RUN"
echo "Log: $LOG_PATH"
