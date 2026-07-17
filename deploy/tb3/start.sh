#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TB3_ROLE="${TB3_ROLE:-tb3}"
source "$SCRIPT_DIR/../lib/load_env.sh"
source "$SCRIPT_DIR/../lib/runtime.sh"

ensure_role_state_writable_with_sudo tb3
python3 "$REPO_ROOT/deploy/host_manifest.py" render-fastdds \
  --manifest "$TB3_HOST_MANIFEST" --role tb3 --repo-root "$REPO_ROOT" \
  --output "$HOST_FASTDDS_PROFILE"
prune_runtime_logs "$TB3_RUNTIME_LOG_DIR"
write_role_state tb3 starting "starting bringup, device/UI stack, and dry-run executor"
trap 'write_role_state tb3 failed "start failed at line $LINENO"' ERR

cd "$TB3_COMPOSE_DIR"
docker compose up -d turtlebot3

docker exec "$ROS_CONTAINER" bash -lc "
set -e
source /opt/ros/jazzy/setup.bash
cd /workspace/ros2_ws
colcon build --packages-select tb3_multimodal_interaction --symlink-install
"

CONTAINER_RUNTIME_LOG_DIR="$CONTAINER_RUNTIME_LOG_DIR" \
RUNTIME_LOG_RETENTION_DAYS="$RUNTIME_LOG_RETENTION_DAYS" \
RUNTIME_LOG_RETAIN_FILES="$RUNTIME_LOG_RETAIN_FILES" \
TB3_UI_EPIPHANY_LOG="$TB3_RUNTIME_LOG_DIR/tb3_ui_epiphany.log" \
TB3_UI_XORG_LOG="$TB3_RUNTIME_LOG_DIR/tb3_ui_xorg.log" \
TB3_UI_OPENBOX_LOG="$TB3_RUNTIME_LOG_DIR/tb3_ui_openbox.log" \
TB3_UI_IDESK_LOG="$TB3_RUNTIME_LOG_DIR/tb3_ui_idesk.log" \
  bash "$REPO_ROOT/scripts/start_tb3_stack_host.sh" "http://127.0.0.1:$TB3_UI_PORT"
TB3_BEHAVIOR_DRY_RUN="$TB3_BEHAVIOR_DRY_RUN" \
  CONTAINER_RUNTIME_LOG_DIR="$CONTAINER_RUNTIME_LOG_DIR" \
  RUNTIME_LOG_RETENTION_DAYS="$RUNTIME_LOG_RETENTION_DAYS" \
  RUNTIME_LOG_RETAIN_FILES="$RUNTIME_LOG_RETAIN_FILES" \
  bash "$REPO_ROOT/scripts/start_behavior_executor_host.sh"

write_role_state tb3 ready "bringup, UI, and dry-run behavior executor ready"
trap - ERR

echo "TB3 stack ready: http://$TB3_IP:$TB3_UI_PORT/"
echo "Behavior dry_run=$TB3_BEHAVIOR_DRY_RUN"
