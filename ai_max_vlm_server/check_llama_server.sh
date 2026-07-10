#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-192.168.64.246}"
PORT="${2:-18082}"
BASE_URL="http://$HOST:$PORT"

echo "Checking $BASE_URL"
curl -fsS "$BASE_URL/health" || curl -fsS "$BASE_URL/v1/models"
echo
