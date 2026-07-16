#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

TIMEOUT_S="${1:-30}"
TOPIC_TIMEOUT_S="${ROS_TOPIC_TIMEOUT_S:-6}"
PROBE_PROCESS_TIMEOUT_S="${ROS_GRAPH_PROBE_PROCESS_TIMEOUT_S:-$((TOPIC_TIMEOUT_S + 3))}"
BRINGUP_LOG="${TB3_BRINGUP_LOG:-/tmp/tb3_bringup.log}"
deadline=$((SECONDS + TIMEOUT_S))

while [ "$SECONDS" -lt "$deadline" ]; do
  counts="$(timeout "${PROBE_PROCESS_TIMEOUT_S}s" python3 \
    /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/check_tb3_bringup_graph.py \
    "$TOPIC_TIMEOUT_S" 2>/dev/null || true)"
  read -r cmd_sub odom_pub <<<"$counts"
  if [ "${cmd_sub:-0}" -gt 0 ] 2>/dev/null && [ "${odom_pub:-0}" -gt 0 ] 2>/dev/null; then
    echo "TB3 bringup ready: /cmd_vel subscribers=$cmd_sub /odom publishers=$odom_pub"
    exit 0
  fi
  sleep 0.5
done

echo "TB3 bringup not ready after ${TIMEOUT_S}s"
echo "--- graph probe ---"
timeout "${PROBE_PROCESS_TIMEOUT_S}s" python3 \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/check_tb3_bringup_graph.py \
  "$TOPIC_TIMEOUT_S" 2>/dev/null || true
echo "--- /cmd_vel ---"
timeout "${PROBE_PROCESS_TIMEOUT_S}s" ros2 topic info /cmd_vel 2>/dev/null || true
echo "--- /odom ---"
timeout "${PROBE_PROCESS_TIMEOUT_S}s" ros2 topic info /odom 2>/dev/null || true
echo "--- bringup log ---"
tail -120 "$BRINGUP_LOG" 2>/dev/null || true
exit 1
