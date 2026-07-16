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
export SERVER_DASHBOARD_PORT="${SERVER_DASHBOARD_PORT:-8775}"
export TB3_UI_PORT="${TB3_UI_PORT:-8765}"
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
export SERVER_REPO_DIR="${SERVER_REPO_DIR:-$SERVER_COMPOSE_DIR/workspace/ros2_ws/src/tb3_multimodal_interaction}"
export TB3_REPO_DIR="${TB3_REPO_DIR:-$TB3_COMPOSE_DIR/workspace/ros2_ws/src/tb3_multimodal_interaction}"
export AI_MAX_REPO_DIR="${AI_MAX_REPO_DIR:-$AI_MAX_ROOT/tb3-multimodal-interaction}"
export LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$AI_MAX_ROOT/llama.cpp}"
export LLAMA_SERVER="${LLAMA_SERVER:-$LLAMA_CPP_DIR/build/bin/llama-server}"
export VLM_MODEL_PATH="${VLM_MODEL_PATH:-}"
export VLM_MMPROJ_PATH="${VLM_MMPROJ_PATH:-}"
export SENSEVOICE_MODEL_DIR="${SENSEVOICE_MODEL_DIR:-$SERVER_COMPOSE_DIR/model_cache/SenseVoiceSmall}"
export TB3_CAMERA_DEVICE="${TB3_CAMERA_DEVICE:-/dev/video0}"
export TB3_OPENCR_DEVICE="${TB3_OPENCR_DEVICE:-/dev/ttyACM0}"
export TB3_LIDAR_DEVICE="${TB3_LIDAR_DEVICE:-/dev/tb3_lidar}"
export TB3_MIC_ALSA_DEVICE="${TB3_MIC_ALSA_DEVICE:-plughw:CARD=Device,DEV=0}"
export TB3_SPEAKER_ALSA_DEVICE="${TB3_SPEAKER_ALSA_DEVICE:-plughw:CARD=UACDemoV10,DEV=0}"
export TB3_DISPLAY="${TB3_DISPLAY:-:0}"
export NTP_REQUIRED="${NTP_REQUIRED:-true}"
export VLM_BASE_URL="${VLM_BASE_URL:-http://$AI_MAX_IP:$VLM_PORT}"
export AI_MAX_RUNTIME_LOG_DIR="${AI_MAX_RUNTIME_LOG_DIR:-$AI_MAX_ROOT/runtime_logs/tb3_multimodal_interaction}"
export SERVER_RUNTIME_LOG_DIR="${SERVER_RUNTIME_LOG_DIR:-$SERVER_COMPOSE_DIR/workspace/runtime_logs/tb3_multimodal_interaction}"
export TB3_RUNTIME_LOG_DIR="${TB3_RUNTIME_LOG_DIR:-$TB3_COMPOSE_DIR/workspace/runtime_logs/tb3_multimodal_interaction}"
export CONTAINER_RUNTIME_LOG_DIR="${CONTAINER_RUNTIME_LOG_DIR:-/workspace/runtime_logs/tb3_multimodal_interaction}"
export RUNTIME_LOG_RETENTION_DAYS="${RUNTIME_LOG_RETENTION_DAYS:-14}"
export RUNTIME_LOG_RETAIN_FILES="${RUNTIME_LOG_RETAIN_FILES:-20}"
export ROLE_STARTUP_GRACE_S="${ROLE_STARTUP_GRACE_S:-180}"
