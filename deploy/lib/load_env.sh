#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  source "$REPO_ROOT/.env"
  set +a
fi

export AI_MAX_IP="${AI_MAX_IP:-192.168.64.246}"
export SERVER_PC_IP="${SERVER_PC_IP:-192.168.250.30}"
export TB3_IP="${TB3_IP:-192.168.250.10}"
export VLM_MODEL="${VLM_MODEL:-qwen3vl8b}"
export VLM_PORT="${VLM_PORT:-18082}"
export VLM_CONTEXT_SIZE="${VLM_CONTEXT_SIZE:-4096}"
export VLM_GPU_LAYERS="${VLM_GPU_LAYERS:-999}"
export VLM_WAIT_TIMEOUT_S="${VLM_WAIT_TIMEOUT_S:-180}"
export VLM_DASHBOARD_PORT="${VLM_DASHBOARD_PORT:-18181}"
export ROS_CONTAINER="${ROS_CONTAINER:-turtlebot3}"
export SERVER_COMPOSE_DIR="${SERVER_COMPOSE_DIR:-/home/user/ROS_Cui/turtlebot3/docker/jazzy}"
export TB3_COMPOSE_DIR="${TB3_COMPOSE_DIR:-/home/turtlebot3/turtlebot3/docker/jazzy}"
export AI_MAX_ROOT="${AI_MAX_ROOT:-/home/user/ROS_Cui}"
export VLM_BASE_URL="${VLM_BASE_URL:-http://$AI_MAX_IP:$VLM_PORT}"
