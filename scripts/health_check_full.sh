#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

MODE="${1:-full}"
TOPIC_TIMEOUT_S="${ROS_TOPIC_TIMEOUT_S:-4}"
TOPIC_RETRY_S="${ROS_TOPIC_RETRY_S:-12}"
FAIL=0

count_publishers() {
  (timeout "${TOPIC_TIMEOUT_S}s" ros2 topic info "$1" 2>/dev/null || true) |
    awk '/Publisher count:/ {print $3; exit}'
}

count_subscribers() {
  (timeout "${TOPIC_TIMEOUT_S}s" ros2 topic info "$1" 2>/dev/null || true) |
    awk '/Subscription count:/ {print $3; exit}'
}

wait_count_publishers() {
  local topic="$1"
  local deadline=$((SECONDS + TOPIC_RETRY_S))
  local count
  while [ "$SECONDS" -le "$deadline" ]; do
    count="$(count_publishers "$topic")"
    if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
      echo "$count"
      return 0
    fi
    sleep 1
  done
  echo "${count:-0}"
}

wait_count_subscribers() {
  local topic="$1"
  local deadline=$((SECONDS + TOPIC_RETRY_S))
  local count
  while [ "$SECONDS" -le "$deadline" ]; do
    count="$(count_subscribers "$topic")"
    if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
      echo "$count"
      return 0
    fi
    sleep 1
  done
  echo "${count:-0}"
}

require_pub() {
  local topic="$1"
  local count
  count="$(wait_count_publishers "$topic")"
  if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
    echo "ok pub $topic $count"
  else
    echo "missing pub $topic"
    FAIL=1
  fi
}

require_sub() {
  local topic="$1"
  local count
  count="$(wait_count_subscribers "$topic")"
  if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
    echo "ok sub $topic $count"
  else
    echo "missing sub $topic"
    FAIL=1
  fi
}

require_cmd_vel_sub() {
  local topic
  local count
  for topic in /cmd_vel /robot_a/cmd_vel /robot_b/cmd_vel; do
    count="$(wait_count_subscribers "$topic")"
    if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
      echo "ok cmd_vel_sub $topic $count"
      return 0
    fi
  done
  echo "missing cmd_vel subscriber"
  FAIL=1
}

require_cmd_vel_sub
require_pub /odom
require_sub /robot_motion/action_cmd
require_sub /robot_expression/trigger
require_sub /robot_face/expression
require_pub /robot_camera/jpeg
require_pub /robot_audio/pcm
require_sub /robot_speech/wav

if [ "$MODE" = "full" ]; then
  require_sub /robot_tts/request
  require_pub /robot_tts/status
  require_sub /robot_asr/request
  require_pub /robot_asr/status
fi

if curl -fsS --max-time 1 http://127.0.0.1:8765/state.json >/dev/null 2>&1; then
  echo "ok tb3_face_ui http://127.0.0.1:8765/state.json"
else
  echo "missing tb3_face_ui http://127.0.0.1:8765/state.json"
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo "TB3_STACK_HEALTH_FAIL"
  exit 1
fi

echo "TB3_STACK_HEALTH_PASS"
