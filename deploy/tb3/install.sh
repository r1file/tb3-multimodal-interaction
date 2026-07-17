#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TB3_ROLE="${TB3_ROLE:-tb3}"
source "$SCRIPT_DIR/../lib/load_env.sh"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TB3_COMPOSE_DIR/manifest_runtime_backup_$STAMP"
mkdir -p "$BACKUP_DIR"
mkdir -p "$TB3_RUNTIME_LOG_DIR"
python3 "$REPO_ROOT/deploy/host_manifest.py" render-fastdds \
  --manifest "$TB3_HOST_MANIFEST" --role tb3 --repo-root "$REPO_ROOT" \
  --output "$HOST_FASTDDS_PROFILE"

for path in "$TB3_COMPOSE_DIR/docker-compose.yml" "$TB3_COMPOSE_DIR"/Dockerfile*; do
  if [[ -e "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/"
  fi
done

install -m 0644 "$SCRIPT_DIR/docker/docker-compose.yml" "$TB3_COMPOSE_DIR/docker-compose.yml"
install -m 0644 "$SCRIPT_DIR/docker/Dockerfile.av-tools" "$TB3_COMPOSE_DIR/Dockerfile.av-tools"
mkdir -p "$TB3_HOME_DIR/.idesktop" "$TB3_HOME_DIR/.config/openbox" "$TB3_HOME_DIR/tb3_ui"
install -m 0644 "$SCRIPT_DIR/tb3-web-ui.lnk" "$TB3_HOME_DIR/.idesktop/tb3-web-ui.lnk"
install -m 0755 "$SCRIPT_DIR/start_tb3_web_ui.sh" "$TB3_HOME_DIR/tb3_ui/start_tb3_web_ui.sh"
sed -i \
  -e "s|__TB3_REPO_DIR__|$TB3_REPO_DIR|g" \
  -e "s|__TB3_HOST_MANIFEST__|$TB3_HOST_MANIFEST|g" \
  "$TB3_HOME_DIR/tb3_ui/start_tb3_web_ui.sh"
sed -i \
  -e "s|__TB3_HOME_DIR__|$TB3_HOME_DIR|g" \
  -e "s|__TB3_UI_PORT__|$TB3_UI_PORT|g" \
  "$TB3_HOME_DIR/.idesktop/tb3-web-ui.lnk"
install -m 0644 "$SCRIPT_DIR/openbox-autostart" "$TB3_HOME_DIR/.config/openbox/autostart"

echo "TB3 runtime configuration installed."
echo "Backup: $BACKUP_DIR"
