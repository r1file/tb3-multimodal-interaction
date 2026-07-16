#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-turtlebot3}"
DRY_RUN="${TB3_BEHAVIOR_DRY_RUN:-true}"
RUNTIME_LOG_DIR="${CONTAINER_RUNTIME_LOG_DIR:-/workspace/runtime_logs/tb3_multimodal_interaction}"
LOG_PATH="${LOG_PATH:-$RUNTIME_LOG_DIR/behavior_executor.log}"
PID_PATH="${PID_PATH:-$RUNTIME_LOG_DIR/behavior_executor.pid}"
RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:-14}"
RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:-20}"

docker exec "$CONTAINER" python3 \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/stop_matching_processes.py \
  behavior_executor_node
docker exec "$CONTAINER" bash \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/prepare_runtime_log.sh \
  "$LOG_PATH" "$RETENTION_DAYS" "$RETAIN_FILES"

docker exec "$CONTAINER" bash -lc "
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
set -u
mkdir -p '$(dirname "$PID_PATH")'
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
