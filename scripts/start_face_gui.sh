#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash

exec ros2 run tb3_multimodal_interaction face_display_node
