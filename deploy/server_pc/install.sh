#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TB3_ROLE="${TB3_ROLE:-server_pc}"
source "$SCRIPT_DIR/../lib/load_env.sh"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$SERVER_COMPOSE_DIR/manifest_runtime_backup_$STAMP"
mkdir -p "$BACKUP_DIR"
mkdir -p "$SERVER_RUNTIME_LOG_DIR"
python3 "$REPO_ROOT/deploy/host_manifest.py" render-fastdds \
  --manifest "$TB3_HOST_MANIFEST" --role server_pc --repo-root "$REPO_ROOT" \
  --output "$HOST_FASTDDS_PROFILE"

for path in "$SERVER_COMPOSE_DIR/docker-compose.yml" "$SERVER_COMPOSE_DIR"/Dockerfile*; do
  if [[ -e "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/"
  fi
done

install -m 0644 "$SCRIPT_DIR/docker/docker-compose.yml" "$SERVER_COMPOSE_DIR/docker-compose.yml"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.asr" "$SERVER_COMPOSE_DIR/Dockerfile.asr"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.av-tools" "$SERVER_COMPOSE_DIR/Dockerfile.av-tools"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.tts" "$SERVER_COMPOSE_DIR/Dockerfile.tts"

echo "Server PC runtime configuration installed."
echo "Backup: $BACKUP_DIR"
