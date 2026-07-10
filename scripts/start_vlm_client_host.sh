#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-turtlebot3}"
LLAMA_BASE_URL="${VLM_BASE_URL:-http://192.168.64.246:18082}"
MODEL="${VLM_MODEL:-qwen3vl8b}"
LOG_DIR="${VLM_LOG_DIR:-/tmp/vlm_client_logs}"
LOG_PATH="${LOG_PATH:-/tmp/vlm_client.log}"
PID_PATH="${PID_PATH:-/tmp/vlm_client.pid}"

docker exec "$CONTAINER" bash -lc "
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
set -u
mkdir -p '$LOG_DIR'
if [ -s '$PID_PATH' ]; then
  old_pid=\$(cat '$PID_PATH' || true)
  if [ -n \"\$old_pid\" ]; then
    kill \"\$old_pid\" >/dev/null 2>&1 || true
    sleep 0.5
  fi
fi
ps -eo pid,args | awk '/vlm_behavior_client_node/ && !/bash -lc/ && !/awk/ {print \$1}' | xargs -r kill >/dev/null 2>&1 || true
sleep 0.5
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
