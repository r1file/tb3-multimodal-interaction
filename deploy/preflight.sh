#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: bash deploy/preflight.sh <ai_max|server_pc|tb3> [--phase install|runtime]

install: verify host prerequisites, external assets, routes, devices, and ports.
runtime: include service health and ROS discovery checks after startup.
EOF
}

ROLE="${1:-}"
PHASE="install"
if [[ $# -gt 0 ]]; then
  shift
fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase)
      PHASE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$ROLE" in
  ai_max|server_pc|tb3) ;;
  *)
    echo "Role must be ai_max, server_pc, or tb3." >&2
    usage >&2
    exit 2
    ;;
esac
case "$PHASE" in
  install|runtime) ;;
  *)
    echo "Phase must be install or runtime." >&2
    exit 2
    ;;
esac

FAIL_COUNT=0
WARN_COUNT=0

pass() {
  printf 'PASS  %s\n' "$*"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf 'WARN  %s\n' "$*"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf 'FAIL  %s\n' "$*" >&2
}

require_command() {
  local command_name="$1"
  local install_hint="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    pass "command '$command_name' is available"
  else
    fail "missing command '$command_name'; $install_hint"
  fi
}

require_dir() {
  local path="$1"
  local hint="$2"
  if [[ -d "$path" ]]; then
    pass "directory exists: $path"
  else
    fail "missing directory: $path; $hint"
  fi
}

require_file() {
  local path="$1"
  local hint="$2"
  if [[ -s "$path" ]]; then
    pass "file exists and is non-empty: $path"
  else
    fail "missing or empty file: $path; $hint"
  fi
}

require_executable() {
  local path="$1"
  local hint="$2"
  if [[ -x "$path" ]]; then
    pass "executable exists: $path"
  else
    fail "missing or non-executable file: $path; $hint"
  fi
}

check_port_value() {
  local name="$1"
  local value="$2"
  if [[ "$value" =~ ^[0-9]+$ ]] && ((value >= 1 && value <= 65535)); then
    pass "$name=$value is a valid TCP port"
  else
    fail "$name='$value' is invalid; set an integer from 1 to 65535 in .env"
  fi
}

check_ip_value() {
  local name="$1"
  local value="$2"
  if [[ "$value" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    pass "$name=$value has IPv4 syntax"
  else
    fail "$name='$value' is invalid; set a reachable IPv4 address in .env"
  fi
}

check_local_address() {
  local expected_ip="$1"
  if ! command -v ip >/dev/null 2>&1; then
    fail "cannot verify local address $expected_ip because command 'ip' is missing; install iproute2"
  elif ip -4 -o addr show 2>/dev/null | awk '{print $4}' | grep -Eq "^${expected_ip//./\\.}/"; then
    pass "configured role address is present locally: $expected_ip"
  else
    fail "configured role address $expected_ip is not assigned to this host; correct .env or network configuration"
  fi
}

check_route() {
  local host="$1"
  local label="$2"
  if command -v ping >/dev/null 2>&1 && ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
    pass "$label is reachable by ICMP: $host"
  else
    fail "$label is unreachable at $host; check power, address, VLAN/forwarding, and host firewall"
  fi
}

port_is_listening() {
  local port="$1"
  ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)$port$"
}

check_local_http_port() {
  local port="$1"
  local path="$2"
  local label="$3"
  local start_hint="$4"
  if port_is_listening "$port"; then
    if curl -fsS --max-time 3 "http://127.0.0.1:$port$path" >/dev/null 2>&1; then
      pass "$label owns TCP $port and responds at $path"
    else
      fail "TCP $port is occupied but $label does not respond at $path; identify it with 'sudo ss -ltnp sport = :$port'"
    fi
  elif [[ "$PHASE" == "runtime" ]]; then
    fail "$label is not listening on TCP $port; $start_hint"
  else
    pass "TCP $port is available for $label"
  fi
}

check_http() {
  local url="$1"
  local label="$2"
  local hint="$3"
  if curl -fsS --max-time 4 "$url" >/dev/null 2>&1; then
    pass "$label is healthy: $url"
  else
    fail "$label is not healthy at $url; $hint"
  fi
}

check_ntp() {
  if [[ "$NTP_REQUIRED" != "true" ]]; then
    warn "NTP_REQUIRED=$NTP_REQUIRED; synchronized wall clocks are not enforced"
    return
  fi
  if ! command -v timedatectl >/dev/null 2>&1; then
    fail "timedatectl is missing; install/enable systemd-timesyncd or set NTP_REQUIRED=false only for an isolated rehearsal"
    return
  fi
  local synchronized
  synchronized="$(timedatectl show -p NTPSynchronized --value 2>/dev/null)"
  if [[ "$synchronized" == "yes" ]]; then
    pass "system clock reports NTPSynchronized=yes"
    local ntp_line
    ntp_line="$(timedatectl timesync-status 2>/dev/null | awk '/Server:|Offset:/{gsub(/^[[:space:]]+/, ""); printf "%s ", $0}')"
    [[ -n "$ntp_line" ]] && printf 'INFO  %s\n' "$ntp_line"
  else
    fail "system clock is not NTP-synchronized; run 'sudo systemctl enable --now systemd-timesyncd' and wait for timedatectl to report yes"
  fi
}

check_docker() {
  require_command docker "install Docker Engine and the Compose plugin"
  if ! command -v docker >/dev/null 2>&1; then
    return
  fi
  if docker info >/dev/null 2>&1; then
    pass "Docker daemon is reachable by the current user"
  else
    fail "Docker daemon is unavailable to this user; start Docker and fix docker-group permissions"
  fi
  if docker compose version >/dev/null 2>&1; then
    pass "Docker Compose plugin is available"
  else
    fail "'docker compose' is unavailable; install the Docker Compose plugin"
  fi
}

check_compose_services() {
  local compose_dir="$1"
  shift
  local services
  services="$(cd "$compose_dir" 2>/dev/null && docker compose config --services 2>/dev/null)"
  if [[ -z "$services" ]]; then
    fail "Docker Compose configuration is invalid or unreadable in $compose_dir; run 'cd $compose_dir && docker compose config'"
    return
  fi
  local service
  for service in "$@"; do
    if grep -qx "$service" <<<"$services"; then
      pass "Compose service is defined: $service"
    else
      fail "Compose service '$service' is missing in $compose_dir/docker-compose.yml; rerun the role install script"
    fi
  done
}

check_repo() {
  local configured_path="$1"
  require_dir "$configured_path" "clone r1file/tb3-multimodal-interaction at this configured path"
  if git -C "$configured_path" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    pass "Git checkout is valid: $configured_path ($(git -C "$configured_path" rev-parse --short HEAD 2>/dev/null))"
  else
    fail "$configured_path is not a Git checkout; perform a fresh clone before deployment"
  fi
  if [[ -d "$configured_path/tb3_week2_executor" || -d "$(dirname "$configured_path")/tb3_week2_executor" ]]; then
    warn "legacy tb3_week2_executor is present; do not source, build, or copy from it during this deployment"
  else
    pass "no legacy tb3_week2_executor directory is used by this checkout"
  fi
}

check_fastdds_profile() {
  local checkout="$1"
  local profile="$checkout/config/fastdds_initial_peers.xml"
  require_file "$profile" "restore the tracked Fast DDS initial-peers profile"
  [[ -s "$profile" ]] || return
  local peer
  for peer in "$SERVER_PC_IP" "$TB3_IP"; do
    if grep -Fq "<address>$peer</address>" "$profile"; then
      pass "Fast DDS profile includes configured peer: $peer"
    else
      fail "Fast DDS profile does not include configured peer $peer; update config/fastdds_initial_peers.xml after changing network addresses"
    fi
  done
}

check_ros_runtime() {
  local mode="$1"
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$ROS_CONTAINER"; then
    fail "ROS container '$ROS_CONTAINER' is not running; start the role before runtime preflight"
    return
  fi
  pass "ROS container is running: $ROS_CONTAINER"
  local ros_setup="source /opt/ros/jazzy/setup.bash && source /workspace/ros2_ws/install/setup.bash && source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh"
  if [[ "$mode" == "server" ]]; then
    if docker exec "$ROS_CONTAINER" bash -lc "$ros_setup && timeout 8s ros2 node list | grep -q ." >/dev/null 2>&1; then
      pass "ROS 2 discovery returns nodes in domain $ROS_DOMAIN_ID"
    else
      fail "ROS 2 discovery returned no nodes; verify ROS_DOMAIN_ID=$ROS_DOMAIN_ID, SUBNET routing, and Fast DDS peers"
    fi
    local topics
    topics="$(docker exec "$ROS_CONTAINER" bash -lc "$ros_setup && timeout 8s ros2 topic list" 2>/dev/null)"
    local topic
    for topic in /odom /robot_camera/jpeg /robot_audio/pcm /robot_asr/status /robot_tts/status /robot_behavior/plan; do
      if grep -qx "$topic" <<<"$topics"; then
        pass "ROS topic is discoverable from Server PC: $topic"
      else
        fail "ROS topic is not discoverable from Server PC: $topic; verify the owning node and DDS route"
      fi
    done
  else
    local nodes
    nodes="$(docker exec "$ROS_CONTAINER" bash -lc "$ros_setup && timeout 10s ros2 node list" 2>/dev/null)"
    local node
    for node in /turtlebot3_node /diff_drive_controller /motion_controller_node /camera_capture_node /mic_capture_node /speech_player_node /face_display_node; do
      if grep -qx "$node" <<<"$nodes"; then
        pass "ROS node is discoverable from TB3: $node"
      else
        fail "ROS node is not discoverable from TB3: $node; inspect the owning launch log and DDS configuration"
      fi
    done
    local topics
    topics="$(docker exec "$ROS_CONTAINER" bash -lc "$ros_setup && timeout 10s ros2 topic list" 2>/dev/null)"
    local topic
    for topic in /odom /robot_camera/jpeg /robot_audio/pcm /robot_motion/action_cmd /robot_face/expression /robot_speech/wav; do
      if grep -qx "$topic" <<<"$topics"; then
        pass "ROS topic is discoverable from TB3: $topic"
      else
        fail "ROS topic is not discoverable from TB3: $topic; verify the owning node and DDS route"
      fi
    done
    if docker exec "$ROS_CONTAINER" bash -lc "$ros_setup && timeout 10s ros2 topic echo /odom --once | grep -qm1 '^header:'" >/dev/null 2>&1; then
      pass "live /odom data is available from the TurtleBot3 base"
    else
      fail "no live /odom sample arrived within 10 seconds; inspect TurtleBot3 bringup and OpenCR connectivity"
    fi
  fi
}

if [[ ! -f "$REPO_ROOT/.env" ]]; then
  fail "missing $REPO_ROOT/.env; copy .env.example to .env and verify every role-specific value before building"
fi

# load_env.sh also supplies safe defaults so all remaining failures can be shown
# in one run even when .env is incomplete.
source "$SCRIPT_DIR/lib/load_env.sh"
set +e

printf 'Preflight role=%s phase=%s repo=%s\n' "$ROLE" "$PHASE" "$REPO_ROOT"

require_command git "install git"
require_command curl "install curl"
require_command ss "install iproute2"
require_command ping "install iputils-ping"
check_docker

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]]; then
    pass "supported OS detected: ${PRETTY_NAME:-Ubuntu 24.04}"
  else
    fail "tested OS is Ubuntu 24.04; detected ${PRETTY_NAME:-unknown}; use the tested base or document and validate the deviation"
  fi
else
  fail "cannot read /etc/os-release; the tested hosts run Ubuntu 24.04"
fi

check_ip_value AI_MAX_IP "$AI_MAX_IP"
check_ip_value SERVER_PC_IP "$SERVER_PC_IP"
check_ip_value TB3_IP "$TB3_IP"
check_port_value VLM_PORT "$VLM_PORT"
check_port_value VLM_DASHBOARD_PORT "$VLM_DASHBOARD_PORT"
check_port_value SERVER_DASHBOARD_PORT "$SERVER_DASHBOARD_PORT"
check_port_value TB3_UI_PORT "$TB3_UI_PORT"

if [[ "$ROS_DOMAIN_ID" =~ ^[0-9]+$ ]] && ((ROS_DOMAIN_ID >= 0 && ROS_DOMAIN_ID <= 232)); then
  pass "ROS_DOMAIN_ID=$ROS_DOMAIN_ID is valid"
else
  fail "ROS_DOMAIN_ID='$ROS_DOMAIN_ID' is invalid; choose 0..232 in .env and use the same value on Server PC and TB3"
fi
check_ntp

case "$ROLE" in
  ai_max)
    check_local_address "$AI_MAX_IP"
    check_repo "$AI_MAX_REPO_DIR"
    require_dir "$LLAMA_CPP_DIR" "clone the tested llama.cpp revision listed in docs/prerequisites.md"
    require_executable "$LLAMA_SERVER" "build llama.cpp with llama-server support and set LLAMA_SERVER in .env"
    if [[ -n "$VLM_MODEL_PATH" ]]; then
      require_file "$VLM_MODEL_PATH" "download the tested Qwen GGUF and set VLM_MODEL_PATH in .env"
    else
      fail "VLM_MODEL_PATH is empty; set the absolute Qwen GGUF path in .env"
    fi
    if [[ -n "$VLM_MMPROJ_PATH" ]]; then
      require_file "$VLM_MMPROJ_PATH" "download the matching mmproj GGUF and set VLM_MMPROJ_PATH in .env"
    else
      fail "VLM_MMPROJ_PATH is empty; set the matching mmproj GGUF path in .env"
    fi
    check_local_http_port "$VLM_PORT" /health "llama-server" "run 'bash deploy/ai_max/start.sh'"
    check_local_http_port "$VLM_DASHBOARD_PORT" / "AI Max dashboard" "run 'bash deploy/ai_max/start.sh'"
    ;;
  server_pc)
    check_local_address "$SERVER_PC_IP"
    check_repo "$SERVER_REPO_DIR"
    check_fastdds_profile "$SERVER_REPO_DIR"
    require_dir "$SERVER_COMPOSE_DIR" "clone ROBOTIS turtlebot3 and set SERVER_COMPOSE_DIR in .env"
    require_file "$SENSEVOICE_MODEL_DIR/model.pt" "place SenseVoiceSmall under the configured model cache before docker compose build"
    check_compose_services "$SERVER_COMPOSE_DIR" turtlebot3 tb3_asr tb3_tts
    check_route "$AI_MAX_IP" "AI Max"
    check_route "$TB3_IP" "TurtleBot3"
    check_local_http_port "$SERVER_DASHBOARD_PORT" /status.json "Server dashboard" "run 'bash deploy/server_pc/start.sh'"
    if [[ "$PHASE" == "runtime" ]]; then
      check_http "http://$AI_MAX_IP:$VLM_PORT/health" "AI Max VLM" "start AI Max first and verify network forwarding"
      check_ros_runtime server
    fi
    ;;
  tb3)
    check_local_address "$TB3_IP"
    check_repo "$TB3_REPO_DIR"
    check_fastdds_profile "$TB3_REPO_DIR"
    require_dir "$TB3_COMPOSE_DIR" "clone ROBOTIS turtlebot3 and set TB3_COMPOSE_DIR in .env"
    check_compose_services "$TB3_COMPOSE_DIR" turtlebot3
    require_command arecord "install alsa-utils"
    require_command aplay "install alsa-utils"
    require_command xhost "install x11-xserver-utils"
    require_command openbox "install openbox"
    require_command epiphany "install epiphany-browser"
    for device_spec in \
      "$TB3_CAMERA_DEVICE|camera" \
      "$TB3_OPENCR_DEVICE|OpenCR" \
      "$TB3_LIDAR_DEVICE|LiDAR"; do
      device_path="${device_spec%%|*}"
      device_label="${device_spec##*|}"
      if [[ -e "$device_path" ]]; then
        pass "$device_label device exists: $device_path"
      else
        fail "$device_label device is missing at $device_path; reconnect hardware or correct the device path in .env"
      fi
    done
    mic_card="${TB3_MIC_ALSA_DEVICE#*CARD=}"
    mic_card="${mic_card%%,*}"
    if arecord -l 2>/dev/null | grep -Fq "$mic_card"; then
      pass "microphone ALSA card is visible: $TB3_MIC_ALSA_DEVICE"
    else
      fail "microphone ALSA card '$mic_card' is not visible; run 'arecord -l' and correct TB3_MIC_ALSA_DEVICE"
    fi
    speaker_card="${TB3_SPEAKER_ALSA_DEVICE#*CARD=}"
    speaker_card="${speaker_card%%,*}"
    if aplay -l 2>/dev/null | grep -Fq "$speaker_card"; then
      pass "speaker ALSA card is visible: $TB3_SPEAKER_ALSA_DEVICE"
    else
      fail "speaker ALSA card '$speaker_card' is not visible; run 'aplay -l' and correct TB3_SPEAKER_ALSA_DEVICE"
    fi
    display_number="${TB3_DISPLAY#:}"
    display_number="${display_number%%.*}"
    if [[ -S "/tmp/.X11-unix/X$display_number" ]]; then
      pass "display socket exists for TB3_DISPLAY=$TB3_DISPLAY"
    else
      fail "display socket /tmp/.X11-unix/X$display_number is missing; start the local X session or correct TB3_DISPLAY"
    fi
    check_route "$SERVER_PC_IP" "Server PC"
    check_route "$AI_MAX_IP" "AI Max"
    check_local_http_port "$TB3_UI_PORT" /state.json "TB3 face/UI service" "run 'bash deploy/tb3/start.sh'"
    if [[ "$PHASE" == "runtime" ]]; then
      check_http "http://$SERVER_PC_IP:$SERVER_DASHBOARD_PORT/status.json" "Server dashboard" "start Server PC before TB3"
      check_http "http://$AI_MAX_IP:$VLM_PORT/health" "AI Max VLM" "start AI Max before TB3"
      check_ros_runtime tb3
    fi
    ;;
esac

if ((FAIL_COUNT > 0)); then
  printf 'PREFLIGHT_FAIL role=%s phase=%s failures=%d warnings=%d\n' "$ROLE" "$PHASE" "$FAIL_COUNT" "$WARN_COUNT" >&2
  exit 1
fi

printf 'PREFLIGHT_PASS role=%s phase=%s warnings=%d\n' "$ROLE" "$PHASE" "$WARN_COUNT"
