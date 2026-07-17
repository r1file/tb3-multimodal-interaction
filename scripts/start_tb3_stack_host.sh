#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="${ROS_CONTAINER:?ROS_CONTAINER is required from the host manifest}"
TB3_UI_PORT="${TB3_UI_PORT:?TB3_UI_PORT is required from the host manifest}"
TB3_CAMERA_DEVICE="${TB3_CAMERA_DEVICE:?TB3_CAMERA_DEVICE is required from the host manifest}"
TB3_MIC_ALSA_DEVICE="${TB3_MIC_ALSA_DEVICE:?TB3_MIC_ALSA_DEVICE is required from the host manifest}"
TB3_SPEAKER_ALSA_DEVICE="${TB3_SPEAKER_ALSA_DEVICE:?TB3_SPEAKER_ALSA_DEVICE is required from the host manifest}"
RUNTIME_LOG_DIR="${CONTAINER_RUNTIME_LOG_DIR:?CONTAINER_RUNTIME_LOG_DIR is required from the host manifest}"
RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:?RUNTIME_LOG_RETENTION_DAYS is required from the host manifest}"
RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:?RUNTIME_LOG_RETAIN_FILES is required from the host manifest}"
BRINGUP_LOG="$RUNTIME_LOG_DIR/tb3_bringup.log"
DEVICE_LOG="$RUNTIME_LOG_DIR/device_stack.log"
BRINGUP_WAIT_S="${TB3_BRINGUP_WAIT_S:-45}"
URL="${1:-http://127.0.0.1:$TB3_UI_PORT}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Error: $CONTAINER container is not running." >&2
  exit 1
fi

echo "Stopping existing TB3 device-stack processes..."
docker exec "$CONTAINER" python3 \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/stop_matching_processes.py \
  device_stack.launch.py start_device_stack.sh motion_controller_node \
  expression_behavior_node face_display_node camera_capture_node mic_capture_node speech_player_node
docker exec "$CONTAINER" bash \
  /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/prepare_runtime_log.sh \
  "$DEVICE_LOG" "$RETENTION_DAYS" "$RETAIN_FILES"

bringup_running=0
if docker exec "$CONTAINER" bash -lc \
  "pgrep -af '[r]os2 launch turtlebot3_bringup robot.launch.py|[t]urtlebot3_ros' >/dev/null"; then
  bringup_running=1
fi

if [ "$bringup_running" -eq 0 ]; then
  echo "No TB3 bringup process found; starting one owned instance."
  docker exec "$CONTAINER" bash \
    /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/prepare_runtime_log.sh \
    "$BRINGUP_LOG" "$RETENTION_DAYS" "$RETAIN_FILES"
  docker exec -d "$CONTAINER" bash -lc \
    "exec bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_tb3_bringup.sh >'$BRINGUP_LOG' 2>&1"
else
  echo "Existing TB3 bringup process found; preserving it and its active log."
fi

echo "Waiting up to ${BRINGUP_WAIT_S}s for TB3 bringup readiness..."
if ! docker exec \
  -e TB3_BRINGUP_LOG="$BRINGUP_LOG" \
  "$CONTAINER" bash -lc \
  "bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/wait_tb3_bringup_ready.sh '$BRINGUP_WAIT_S'"; then
  echo "Error: TB3 bringup is not ready. Log: $BRINGUP_LOG inside $CONTAINER" >&2
  docker exec "$CONTAINER" tail -n 120 "$BRINGUP_LOG" >&2 || true
  exit 1
fi

docker exec -d \
  -e TB3_UI_PORT="$TB3_UI_PORT" \
  -e TB3_CAMERA_DEVICE="$TB3_CAMERA_DEVICE" \
  -e TB3_MIC_ALSA_DEVICE="$TB3_MIC_ALSA_DEVICE" \
  -e TB3_SPEAKER_ALSA_DEVICE="$TB3_SPEAKER_ALSA_DEVICE" \
  -e TB3_CMD_VEL_TOPIC="${TB3_CMD_VEL_TOPIC:?TB3_CMD_VEL_TOPIC is required from the host manifest}" \
  -e TB3_CMD_VEL_CANDIDATES="${TB3_CMD_VEL_CANDIDATES:?TB3_CMD_VEL_CANDIDATES is required from the host manifest}" \
  "$CONTAINER" bash -lc \
  "bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_device_stack.sh >'$DEVICE_LOG' 2>&1"

echo "Waiting for TB3 device-stack discovery..."
if ! docker exec -e TB3_UI_PORT="$TB3_UI_PORT" "$CONTAINER" bash -lc '
    set +u
    source /opt/ros/jazzy/setup.bash
    source /workspace/ros2_ws/install/setup.bash
    source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
    set -u
    required_nodes=(/camera_capture_node /expression_behavior_node /face_display_node /mic_capture_node /motion_controller_node /speech_player_node)
    ready=0
    for _ in $(seq 1 30); do
      nodes="$(timeout 10s ros2 node list --no-daemon --spin-time 5 2>/dev/null || true)"
      ready=1
      for node in "${required_nodes[@]}"; do
        grep -qx "$node" <<<"$nodes" || { ready=0; break; }
      done
      [ "$ready" -eq 1 ] && break
      sleep 1
    done
    [ "$ready" -eq 1 ] || exit 1
    ROS_TOPIC_RETRY_S=6 bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/health_check_full.sh tb3
  '; then
  echo "Error: TB3 device-stack health check failed. Log: $DEVICE_LOG inside $CONTAINER" >&2
  exit 1
fi

exec "$SCRIPT_DIR/start_touch_gui_host.sh" "$URL"
