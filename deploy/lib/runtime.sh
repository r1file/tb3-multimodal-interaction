#!/usr/bin/env bash

runtime_log_dir_for_role() {
  case "$1" in
    ai_max) printf '%s\n' "$AI_MAX_RUNTIME_LOG_DIR" ;;
    server_pc) printf '%s\n' "$SERVER_RUNTIME_LOG_DIR" ;;
    tb3) printf '%s\n' "$TB3_RUNTIME_LOG_DIR" ;;
    *) echo "Unknown role: $1" >&2; return 2 ;;
  esac
}

write_role_state() {
  local role="$1" state="$2" message="${3:-}"
  local log_dir state_path now
  log_dir="$(runtime_log_dir_for_role "$role")"
  state_path="$log_dir/${role}.state"
  now="$(date +%s)"
  mkdir -p "$log_dir"
  message="${message//$'\n'/ }"
  message="${message//|//}"
  printf '%s|%s|%s\n' "$state" "$now" "$message" >"$state_path"
}

ensure_role_state_writable_with_sudo() {
  local role="$1"
  local log_dir state_path owner
  log_dir="$(runtime_log_dir_for_role "$role")"
  state_path="$log_dir/${role}.state"
  owner="$(id -u):$(id -g)"

  if [[ -d "$log_dir" && -w "$log_dir" && ( ! -e "$state_path" || -w "$state_path" ) ]]; then
    return 0
  fi

  sudo -v
  sudo install -d -o "$(id -u)" -g "$(id -g)" -m 0755 "$log_dir"
  if [[ -e "$state_path" ]]; then
    sudo chown "$owner" "$state_path"
  fi
}

prune_runtime_logs() {
  local log_dir="$1"
  mkdir -p "$log_dir"
  find "$log_dir" -type f -name '*.log.*' -mtime "+$RUNTIME_LOG_RETENTION_DAYS" -delete 2>/dev/null || true
  local files
  files="$(find "$log_dir" -type f -name '*.log.*' -print 2>/dev/null | sort -r | tail -n "+$((RUNTIME_LOG_RETAIN_FILES + 1))")"
  if [[ -n "$files" ]]; then
    while IFS= read -r path; do rm -f -- "$path"; done <<<"$files"
  fi
}
