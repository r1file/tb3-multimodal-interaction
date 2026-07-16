#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-turtlebot3}"
LLAMA_BASE_URL="${VLM_BASE_URL:-http://192.168.64.246:18082}"
MODEL="${VLM_MODEL:-qwen3vl8b}"
RUNTIME_LOG_DIR="${CONTAINER_RUNTIME_LOG_DIR:-/workspace/runtime_logs/tb3_multimodal_interaction}"
LOG_DIR="${VLM_LOG_DIR:-$RUNTIME_LOG_DIR/vlm_client_requests}"
LOG_PATH="${LOG_PATH:-$RUNTIME_LOG_DIR/vlm_client.log}"
PID_PATH="${PID_PATH:-$RUNTIME_LOG_DIR/vlm_client.pid}"
RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:-14}"
RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:-20}"

docker exec "$CONTAINER" python3 \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/stop_matching_processes.py \
  vlm_behavior_client_node
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
mkdir -p '$LOG_DIR' '$(dirname "$PID_PATH")'
nohup ros2 run tb3_multimodal_interaction vlm_behavior_client_node --ros-args \
  -p llama_base_url:='$LLAMA_BASE_URL' \
  -p model:='$MODEL' \
  -p publish_plans:=true \
  -p log_dir:='$LOG_DIR' \
  >'$LOG_PATH' 2>&1 </dev/null &
echo \$! >'$PID_PATH'
sleep 1
if ! kill -0 \$(cat '$PID_PATH') >/dev/null 2>&1; then
  echo 'VLM client failed to stay running' >&2
  tail -n 60 '$LOG_PATH' >&2 || true
  exit 1
fi
ps -p \$(cat '$PID_PATH') -o pid=,cmd=
"

echo "VLM client started in $CONTAINER"
echo "Log: $LOG_PATH"
