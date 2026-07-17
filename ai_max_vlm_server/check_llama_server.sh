#!/usr/bin/env bash
set -euo pipefail

HOST="${1:?usage: check_llama_server.sh HOST PORT}"
PORT="${2:?usage: check_llama_server.sh HOST PORT}"
BASE_URL="http://$HOST:$PORT"

echo "Checking $BASE_URL"
curl -fsS "$BASE_URL/health" || curl -fsS "$BASE_URL/v1/models"
echo
