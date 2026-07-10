#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"

cd "$TB3_COMPOSE_DIR"
docker compose up -d "$ROS_CONTAINER"

docker exec "$ROS_CONTAINER" bash -lc "
set -e
source /opt/ros/jazzy/setup.bash
cd /workspace/ros2_ws
colcon build --packages-select tb3_multimodal_interaction --symlink-install
"

docker exec -d "$ROS_CONTAINER" bash -lc \
  'bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/start_tb3_bringup.sh >/tmp/tb3_bringup.log 2>&1'

sudo -v
bash "$REPO_ROOT/scripts/start_tb3_stack_host.sh"
TB3_BEHAVIOR_DRY_RUN="${TB3_BEHAVIOR_DRY_RUN:-true}" \
  bash "$REPO_ROOT/scripts/start_behavior_executor_host.sh"

echo "TB3 stack ready: http://$TB3_IP:8765/"
echo "Behavior dry_run=${TB3_BEHAVIOR_DRY_RUN:-true}"
