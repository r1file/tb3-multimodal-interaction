#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TB3_ROLE="${TB3_ROLE:-tb3}"
source "$SCRIPT_DIR/../lib/load_env.sh"
source "$SCRIPT_DIR/../lib/runtime.sh"

ensure_role_state_writable_with_sudo tb3
write_role_state tb3 stopping "stopping role-owned UI and ROS container"
pkill -x epiphany 2>/dev/null || true
pkill -f '^/usr/lib/.*/WebKit(Network|Web)Process( |$)' 2>/dev/null || true
pkill -x xdg-dbus-proxy 2>/dev/null || true
cd "$TB3_COMPOSE_DIR"
docker compose stop turtlebot3
write_role_state tb3 stopped "role-owned services stopped"
echo "TB3 stopped; Docker daemon, display server, logs, workspace, and backups were retained."
