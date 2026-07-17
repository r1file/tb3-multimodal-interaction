#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/deploy/lib/manifest_path.sh"

usage() {
  cat <<'EOF'
Usage:
  bash deploy/role.sh manifest-init [--output PATH]
  bash deploy/role.sh <ai_max|server_pc|tb3> <install|start|stop|restart|status> [--manifest PATH]

manifest-init creates a non-overwriting manifest template. The default output is
$XDG_CONFIG_HOME/tb3/host-manifest.toml or ~/.config/tb3/host-manifest.toml.
EOF
}

manifest_init() {
  local output="${TB3_HOST_MANIFEST:-}"
  local output_dir=""
  local template="$REPO_ROOT/config/host-manifest.example.toml"

  if [[ -z "$output" ]]; then
    output="$(host_manifest_user_path)" || {
      echo "Cannot determine the user configuration directory; pass --output PATH." >&2
      exit 2
    }
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output)
        output="${2:-}"
        [[ -n "$output" ]] || { echo "--output requires a path" >&2; exit 2; }
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown manifest-init argument: $1" >&2
        usage >&2
        exit 2
        ;;
    esac
  done

  if [[ -e "$output" ]]; then
    echo "Refusing to overwrite existing host manifest: $output" >&2
    echo "Move it aside explicitly, or choose another path with --output PATH." >&2
    exit 2
  fi

  output_dir="$(dirname "$output")"
  if [[ ! -d "$output_dir" ]]; then
    install -d -m 0700 "$output_dir"
  fi
  install -m 0600 "$template" "$output"

  echo "Initialized host manifest template: $output"
  echo "Edit every REPLACE_* value and all three role tables, then validate it with:"
  printf '  python3 deploy/host_manifest.py validate --manifest %q\n' "$output"
  echo "Copy the completed file unchanged to the same path on all three hosts."
}

if [[ "${1:-}" == "manifest-init" ]]; then
  shift
  manifest_init "$@"
  exit 0
fi

ROLE="${1:-}"
ACTION="${2:-}"
MANIFEST="$(resolve_host_manifest_path "$REPO_ROOT")"
if [[ "${3:-}" == "--manifest" ]]; then
  MANIFEST="${4:-}"
  [[ -n "$MANIFEST" ]] || { echo "--manifest requires a path" >&2; exit 2; }
elif [[ -n "${3:-}" ]]; then
  echo "unknown argument: ${3}" >&2
  exit 2
fi
case "$ROLE" in ai_max|server_pc|tb3) ;; *) usage >&2; exit 2;; esac
case "$ACTION" in
  install|start|stop|restart|status) ;;
  *) usage >&2; exit 2 ;;
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
