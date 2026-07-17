#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${TB3_ROLE:?TB3_ROLE must be ai_max, server_pc, or tb3}"

TB3_HOST_MANIFEST="${TB3_HOST_MANIFEST:-$REPO_ROOT/host-manifest.toml}"
if [[ ! -f "$TB3_HOST_MANIFEST" ]]; then
  echo "Missing host manifest: $TB3_HOST_MANIFEST" >&2
  echo "Copy config/host-manifest.example.toml to host-manifest.toml, configure all three roles, and pin [release].commit." >&2
  exit 2
fi

manifest_exports="$(
  python3 "$REPO_ROOT/deploy/host_manifest.py" export-shell \
    --manifest "$TB3_HOST_MANIFEST" \
    --role "$TB3_ROLE" \
    --repo-root "$REPO_ROOT" \
    --require-clean
)"
eval "$manifest_exports"
unset manifest_exports
