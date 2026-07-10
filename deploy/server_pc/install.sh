#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/load_env.sh"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$SERVER_COMPOSE_DIR/p6_runtime_backup_$STAMP"
mkdir -p "$BACKUP_DIR"

for path in "$SERVER_COMPOSE_DIR/container.sh" "$SERVER_COMPOSE_DIR/docker-compose.yml" "$SERVER_COMPOSE_DIR"/Dockerfile*; do
  if [[ -e "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/"
  fi
done

if [[ -d "$SERVER_COMPOSE_DIR/week3_model_cache" && ! -e "$SERVER_COMPOSE_DIR/model_cache" ]]; then
  mv "$SERVER_COMPOSE_DIR/week3_model_cache" "$SERVER_COMPOSE_DIR/model_cache"
fi

install -m 0755 "$SCRIPT_DIR/docker/container.sh" "$SERVER_COMPOSE_DIR/container.sh"
install -m 0644 "$SCRIPT_DIR/docker/docker-compose.yml" "$SERVER_COMPOSE_DIR/docker-compose.yml"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.asr" "$SERVER_COMPOSE_DIR/Dockerfile.asr"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.av-tools" "$SERVER_COMPOSE_DIR/Dockerfile.av-tools"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.tts" "$SERVER_COMPOSE_DIR/Dockerfile.tts"

echo "Server PC runtime configuration installed."
echo "Backup: $BACKUP_DIR"
