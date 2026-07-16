#!/usr/bin/env bash
set -euo pipefail
LOG_PATH="${1:?usage: prepare_runtime_log.sh LOG_PATH [DAYS] [COUNT]}"
RETENTION_DAYS="${2:-14}"
RETAIN_FILES="${3:-20}"
LOG_DIR="$(dirname "$LOG_PATH")"
BASE="$(basename "$LOG_PATH")"

mkdir -p "$LOG_DIR"
if [[ -s "$LOG_PATH" ]]; then
  mv "$LOG_PATH" "$LOG_PATH.$(date +%Y%m%d_%H%M%S)"
else
  rm -f "$LOG_PATH"
fi
touch "$LOG_PATH"
find "$LOG_DIR" -maxdepth 1 -type f -name "$BASE.*" -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
find "$LOG_DIR" -maxdepth 1 -type f -name "$BASE.*" -print 2>/dev/null \
  | sort -r | tail -n "+$((RETAIN_FILES + 1))" | xargs -r rm -f --
