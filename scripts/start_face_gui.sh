#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh

exec ros2 run tb3_multimodal_interaction face_display_node --ros-args \
  -p port:="${TB3_UI_PORT:?TB3_UI_PORT is required}" \
  -p camera_device:="${TB3_CAMERA_DEVICE:?TB3_CAMERA_DEVICE is required}" \
  -p mic_alsa_device:="${TB3_MIC_ALSA_DEVICE:?TB3_MIC_ALSA_DEVICE is required}" \
  -p speaker_alsa_device:="${TB3_SPEAKER_ALSA_DEVICE:?TB3_SPEAKER_ALSA_DEVICE is required}"
