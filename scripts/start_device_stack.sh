#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

if [ -z "${TB3_CMD_VEL_TOPIC:-}" ]; then
  for _ in $(seq 1 4); do
    for candidate in /cmd_vel /robot_a/cmd_vel /robot_b/cmd_vel; do
      subscription_count="$(
        (timeout 1s ros2 topic info "$candidate" 2>/dev/null || true) |
          awk '/Subscription count:/ {print $3; exit}'
      )"
      if [ "${subscription_count:-0}" -gt 0 ] 2>/dev/null; then
        export TB3_CMD_VEL_TOPIC="$candidate"
        break 2
      fi
    done
    sleep 1
  done
fi

export TB3_CMD_VEL_TOPIC="${TB3_CMD_VEL_TOPIC:-/cmd_vel}"
echo "TB3 motion cmd_vel topic: $TB3_CMD_VEL_TOPIC"

exec ros2 launch tb3_multimodal_interaction device_stack.launch.py
