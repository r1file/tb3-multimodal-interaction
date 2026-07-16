#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/deploy/lib/load_env.sh"

ROLE="${1:-}"
ACTION="${2:-}"
case "$ROLE" in ai_max|server_pc|tb3) ;; *) echo "usage: deploy/role.sh ai_max|server_pc|tb3 install|start|stop|restart|status" >&2; exit 2;; esac
case "$ACTION" in
  install|start|stop) exec bash "$REPO_ROOT/deploy/$ROLE/$ACTION.sh" ;;
  restart)
    bash "$REPO_ROOT/deploy/$ROLE/stop.sh"
    exec bash "$REPO_ROOT/deploy/$ROLE/start.sh"
    ;;
  status) exec python3 "$REPO_ROOT/deploy/role_status.py" "$ROLE" ;;
  *) echo "usage: deploy/role.sh ai_max|server_pc|tb3 install|start|stop|restart|status" >&2; exit 2 ;;
esac
