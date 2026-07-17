#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

if [[ "${TB3_CMD_VEL_TOPIC:?TB3_CMD_VEL_TOPIC is required}" == "auto" ]]; then
  IFS=',' read -r -a cmd_vel_candidates <<<"${TB3_CMD_VEL_CANDIDATES:?TB3_CMD_VEL_CANDIDATES is required for auto discovery}"
  discovered_topic=""
  for _ in 1 2; do
    for candidate in "${cmd_vel_candidates[@]}"; do
      subscription_count="$(
        (timeout 8s ros2 topic info "$candidate" --no-daemon --spin-time 5 2>/dev/null || true) |
          awk '/Subscription count:/ {print $3; exit}'
      )"
      if [ "${subscription_count:-0}" -gt 0 ] 2>/dev/null; then
        discovered_topic="$candidate"
        break 2
      fi
    done
    sleep 0.5
  done
  if [[ -z "$discovered_topic" ]]; then
    echo "No cmd_vel subscriber found among manifest candidates: $TB3_CMD_VEL_CANDIDATES" >&2
    exit 1
  fi
  export TB3_CMD_VEL_TOPIC="$discovered_topic"
fi

echo "TB3 motion cmd_vel topic: $TB3_CMD_VEL_TOPIC"

exec ros2 launch tb3_multimodal_interaction device_stack.launch.py
