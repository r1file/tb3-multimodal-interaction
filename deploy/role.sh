#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ROLE="${1:-}"
ACTION="${2:-}"
MANIFEST="${TB3_HOST_MANIFEST:-$REPO_ROOT/host-manifest.toml}"
if [[ "${3:-}" == "--manifest" ]]; then
  MANIFEST="${4:-}"
  [[ -n "$MANIFEST" ]] || { echo "--manifest requires a path" >&2; exit 2; }
elif [[ -n "${3:-}" ]]; then
  echo "unknown argument: ${3}" >&2
  exit 2
fi
case "$ROLE" in ai_max|server_pc|tb3) ;; *) echo "usage: deploy/role.sh ai_max|server_pc|tb3 install|start|stop|restart|status [--manifest PATH]" >&2; exit 2;; esac
case "$ACTION" in
  install|start|stop|restart|status) ;;
  *) echo "usage: deploy/role.sh ai_max|server_pc|tb3 install|start|stop|restart|status [--manifest PATH]" >&2; exit 2 ;;
esac

export TB3_ROLE="$ROLE"
export TB3_HOST_MANIFEST="$MANIFEST"
source "$REPO_ROOT/deploy/lib/load_env.sh"

case "$ACTION" in
  install|start|stop) exec bash "$REPO_ROOT/deploy/$ROLE/$ACTION.sh" ;;
  restart)
    bash "$REPO_ROOT/deploy/$ROLE/stop.sh"
    exec bash "$REPO_ROOT/deploy/$ROLE/start.sh"
    ;;
  status) exec python3 "$REPO_ROOT/deploy/role_status.py" "$ROLE" ;;
esac
