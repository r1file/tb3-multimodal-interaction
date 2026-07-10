#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TB3_COMPOSE_DIR/p6_runtime_backup_$STAMP"
mkdir -p "$BACKUP_DIR"

for path in "$TB3_COMPOSE_DIR/container.sh" "$TB3_COMPOSE_DIR/docker-compose.yml" "$TB3_COMPOSE_DIR"/Dockerfile*; do
  if [[ -e "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/"
  fi
done

install -m 0755 "$SCRIPT_DIR/docker/container.sh" "$TB3_COMPOSE_DIR/container.sh"
install -m 0644 "$SCRIPT_DIR/docker/docker-compose.yml" "$TB3_COMPOSE_DIR/docker-compose.yml"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.av-tools" "$TB3_COMPOSE_DIR/Dockerfile.av-tools"
mkdir -p "$HOME/.idesktop" "$HOME/.config/openbox"
install -m 0644 "$SCRIPT_DIR/tb3-web-ui.lnk" "$HOME/.idesktop/tb3-web-ui.lnk"
install -m 0644 "$SCRIPT_DIR/openbox-autostart" "$HOME/.config/openbox/autostart"

echo "TB3 runtime configuration installed."
echo "Backup: $BACKUP_DIR"
