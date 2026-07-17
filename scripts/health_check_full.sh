#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

MODE="${1:-full}"
TB3_UI_PORT="${TB3_UI_PORT:?TB3_UI_PORT is required from the host manifest}"
TB3_CMD_VEL_CANDIDATES="${TB3_CMD_VEL_CANDIDATES:?TB3_CMD_VEL_CANDIDATES is required from the host manifest}"

python3 /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/check_ros_graph_contract.py "$MODE"

if curl -fsS --max-time 1 "http://127.0.0.1:$TB3_UI_PORT/state.json" >/dev/null 2>&1; then
  echo "ok tb3_face_ui http://127.0.0.1:$TB3_UI_PORT/state.json"
else
  echo "missing tb3_face_ui http://127.0.0.1:$TB3_UI_PORT/state.json"
  exit 1
fi

echo "TB3_STACK_HEALTH_PASS"
