#!/usr/bin/env bash

# Shared host-manifest path policy. Explicit TB3_HOST_MANIFEST always wins;
# otherwise prefer the user configuration directory and retain the historical
# repository-local path as a compatibility fallback.

host_manifest_user_path() {
  local config_home
  if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
    config_home="$XDG_CONFIG_HOME"
  elif [[ -n "${HOME:-}" ]]; then
    config_home="$HOME/.config"
  else
    return 1
  fi
  printf '%s/tb3/host-manifest.toml\n' "$config_home"
}

resolve_host_manifest_path() {
  local repo_root="${1:?repository root is required}"
  local user_path=""

  if [[ -n "${TB3_HOST_MANIFEST:-}" ]]; then
    printf '%s\n' "$TB3_HOST_MANIFEST"
    return 0
  fi

  user_path="$(host_manifest_user_path 2>/dev/null || true)"
  if [[ -n "$user_path" && -f "$user_path" ]]; then
    printf '%s\n' "$user_path"
  elif [[ -f "$repo_root/host-manifest.toml" ]]; then
    printf '%s/host-manifest.toml\n' "$repo_root"
  elif [[ -n "$user_path" ]]; then
    # Report the standard location when nothing exists so the error and
    # manifest-init guidance point at the same path.
    printf '%s\n' "$user_path"
  else
    printf '%s/host-manifest.toml\n' "$repo_root"
  fi
}
