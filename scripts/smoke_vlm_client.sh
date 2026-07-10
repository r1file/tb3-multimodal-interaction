#!/usr/bin/env bash
set -euo pipefail

LOG_PATH="${LOG_PATH:-/tmp/vlm_client.log}"
LLAMA_BASE_URL="${VLM_BASE_URL:-http://192.168.64.246:18082}"
MODEL="${VLM_MODEL:-qwen3vl8b}"
TEXT="${TEXT:-Please greet me, stay still, and use a calm expression.}"
MODE="${MODE:-dry_run}"
INCLUDE_CAMERA="${INCLUDE_CAMERA:-true}"
ACCEPT_FALLBACK="${ACCEPT_FALLBACK:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set +u
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source "$SCRIPT_DIR/ros_env.sh"
set -u

echo "Checking VLM server $LLAMA_BASE_URL"
curl -fsS --max-time 5 "$LLAMA_BASE_URL/health" >/dev/null || curl -fsS --max-time 5 "$LLAMA_BASE_URL/v1/models" >/dev/null

pgrep -f "/tb3_multimodal_interaction/vlm_behavior_client_node" | xargs -r kill >/dev/null 2>&1 || true

ros2 run tb3_multimodal_interaction vlm_behavior_client_node --ros-args \
  -p llama_base_url:="$LLAMA_BASE_URL" \
  -p model:="$MODEL" \
  -p publish_plans:=true \
  >"$LOG_PATH" 2>&1 &
CLIENT_PID=$!

cleanup() {
  kill "$CLIENT_PID" >/dev/null 2>&1 || true
  wait "$CLIENT_PID" >/dev/null 2>&1 || true
  pgrep -f "/tb3_multimodal_interaction/vlm_behavior_client_node" | xargs -r kill >/dev/null 2>&1 || true
}
trap cleanup EXIT

python3 - <<'PY'
import json
import os
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Smoke(Node):
    def __init__(self):
        super().__init__("vlm_client_smoke")
        self.req_pub = self.create_publisher(String, "/robot_ai/response_request", 10)
        self.statuses = []
        self.plans = []
        self.create_subscription(String, "/robot_ai/status", self.on_status, 10)
        self.create_subscription(String, "/robot_behavior/plan", self.on_plan, 10)

    def on_status(self, msg):
        print("AI_STATUS", msg.data, flush=True)
        self.statuses.append(msg.data)

    def on_plan(self, msg):
        print("BEHAVIOR_PLAN", msg.data, flush=True)
        self.plans.append(msg.data)


def spin_until(node, predicate, timeout_s):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if predicate():
            return True
    return False


def status_has(node, state):
    return any(f'"state":"{state}"' in raw for raw in node.statuses)


def max_image_bytes(node):
    values = []
    for raw in node.statuses:
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        if "image_bytes" in payload:
            try:
                values.append(int(payload["image_bytes"]))
            except Exception:
                pass
    return max(values) if values else 0


def main():
    text = os.environ.get("TEXT", "Please greet me, stay still, and use a calm expression.")
    mode = os.environ.get("MODE", "dry_run")
    include_camera = os.environ.get("INCLUDE_CAMERA", "true").lower() == "true"
    accept_fallback = os.environ.get("ACCEPT_FALLBACK", "false").lower() == "true"

    rclpy.init()
    node = Smoke()
    try:
        if not spin_until(node, lambda: node.req_pub.get_subscription_count() > 0, 10.0):
            raise RuntimeError("/robot_ai/response_request has no subscribers")

        msg = String()
        msg.data = json.dumps(
            {
                "request_id": f"vlm_smoke_{int(time.time())}",
                "source": "vlm_client_smoke",
                "mode": mode,
                "text": text,
                "record": False,
                "include_asr": False,
                "include_camera": include_camera,
                "time": time.time(),
            },
            separators=(",", ":"),
        )
        node.req_pub.publish(msg)

        if not spin_until(node, lambda: status_has(node, "published"), 75.0):
            raise RuntimeError("missing /robot_ai/status state=published")
        if include_camera and max_image_bytes(node) <= 0:
            raise RuntimeError("include_camera=true but VLM request used 0 image bytes")
        if not spin_until(node, lambda: bool(node.plans), 5.0):
            raise RuntimeError("missing /robot_behavior/plan")

        plan = json.loads(node.plans[-1])
        if not accept_fallback and plan.get("fallback_used"):
            raise RuntimeError(f"VLM client produced fallback plan: {plan}")
        if not isinstance(plan.get("motion"), list) or not plan["motion"]:
            raise RuntimeError(f"published plan has no motion: {plan}")
        print("VLM_CLIENT_SMOKE_PASS", flush=True)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
PY
