#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
if [ -f /workspace/ros2_ws/install/setup.bash ]; then
  source /workspace/ros2_ws/install/setup.bash
fi
if [ -f /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh ]; then
  source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
else
  unset ROS_DISCOVERY_SERVER
  unset ROS_SUPER_CLIENT
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
fi

ros2 topic pub --once /robot_expression/trigger std_msgs/msg/String "{data: happy}"
ros2 topic pub --once /robot_speech/text std_msgs/msg/String "{data: TB3 speaker test}"
ros2 topic pub --once /robot_motion/action_cmd std_msgs/msg/String "{data: '{\"action\":\"turn_left\",\"duration\":0.5}'}"
sleep 1
ros2 topic pub --once /robot_motion/action_cmd std_msgs/msg/String "{data: stop}"
