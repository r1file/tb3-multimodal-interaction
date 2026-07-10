#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
if [ -f /workspace/ros2_ws/install/setup.bash ]; then
  source /workspace/ros2_ws/install/setup.bash
fi
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger}"

exec ros2 launch turtlebot3_bringup robot.launch.py
