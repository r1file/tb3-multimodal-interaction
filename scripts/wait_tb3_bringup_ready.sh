#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

TIMEOUT_S="${1:-30}"
TOPIC_TIMEOUT_S="${ROS_TOPIC_TIMEOUT_S:-4}"
deadline=$((SECONDS + TIMEOUT_S))

while [ "$SECONDS" -lt "$deadline" ]; do
  cmd_sub="$( (timeout "${TOPIC_TIMEOUT_S}s" ros2 topic info /cmd_vel 2>/dev/null || true) | awk '/Subscription count:/ {print $3; exit}')"
  odom_pub="$( (timeout "${TOPIC_TIMEOUT_S}s" ros2 topic info /odom 2>/dev/null || true) | awk '/Publisher count:/ {print $3; exit}')"
  if [ "${cmd_sub:-0}" -gt 0 ] 2>/dev/null && [ "${odom_pub:-0}" -gt 0 ] 2>/dev/null; then
    echo "TB3 bringup ready: /cmd_vel subscribers=$cmd_sub /odom publishers=$odom_pub"
    exit 0
  fi
  sleep 0.5
done

echo "TB3 bringup not ready after ${TIMEOUT_S}s"
echo "--- /cmd_vel ---"
ros2 topic info /cmd_vel 2>/dev/null || true
echo "--- /odom ---"
ros2 topic info /odom 2>/dev/null || true
echo "--- bringup log ---"
tail -120 /tmp/tb3_bringup.log 2>/dev/null || true
exit 1
