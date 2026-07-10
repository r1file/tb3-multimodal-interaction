#!/usr/bin/env bash
set -eo pipefail

LOG_PATH="${LOG_PATH:-/tmp/behavior_executor_smoke.log}"

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
set -u

rm -f "$LOG_PATH"
pgrep -f "/tb3_multimodal_interaction/behavior_executor_node" | xargs -r kill >/dev/null 2>&1 || true
sleep 1
ros2 run tb3_multimodal_interaction behavior_executor_node --ros-args -p dry_run:=true >"$LOG_PATH" 2>&1 &
EXECUTOR_PID=$!

cleanup() {
  kill "$EXECUTOR_PID" >/dev/null 2>&1 || true
  wait "$EXECUTOR_PID" >/dev/null 2>&1 || true
  pgrep -f "/tb3_multimodal_interaction/behavior_executor_node" | xargs -r kill >/dev/null 2>&1 || true
  sleep 0.5
  pgrep -f "/tb3_multimodal_interaction/behavior_executor_node" | xargs -r kill -9 >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

python3 - <<'PY'
import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SmokeNode(Node):
    def __init__(self):
        super().__init__("behavior_dry_run_smoke")
        self.pub = self.create_publisher(String, "/robot_behavior/plan", 10)
        self.statuses = []
        self.create_subscription(String, "/robot_behavior/status", self.on_status, 10)

    def on_status(self, msg):
        self.statuses.append(msg.data)
        print("STATUS", msg.data, flush=True)


def wait_for_status(node, previous_count, timeout_s):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if len(node.statuses) > previous_count:
            return True
    return False


def wait_for_match(node, matcher, timeout_s):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if any(matcher(raw) for raw in node.statuses):
            return True
    return False


def publish(node, payload):
    deadline = time.monotonic() + 5.0
    while node.pub.get_subscription_count() == 0 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.05)
    if node.pub.get_subscription_count() == 0:
        raise RuntimeError("/robot_behavior/plan has no subscribers")
    msg = String()
    msg.data = payload
    node.pub.publish(msg)
    rclpy.spin_once(node, timeout_sec=0.1)


rclpy.init()
node = SmokeNode()
try:
    valid_plan = {
        "input_id": "behavior_dry_run_valid_001",
        "source": "behavior_smoke",
        "validated": True,
        "fallback_used": False,
        "reply": "I see the object. I will stay here.",
        "emotion": "neutral",
        "tts_style": "calm",
        "face": "neutral",
        "motion": [{"action": "stop", "duration": 0.2}],
    }
    before = len(node.statuses)
    publish(node, json.dumps(valid_plan, separators=(",", ":")))
    if not wait_for_status(node, before, 5.0):
        raise RuntimeError("valid plan produced no /robot_behavior/status")
    if not wait_for_match(
        node,
        lambda raw: '"state":"accepted"' in raw and "behavior_dry_run_valid_001" in raw,
        5.0,
    ):
        raise RuntimeError("valid plan did not reach accepted state")
    if not wait_for_match(
        node,
        lambda raw: '"state":"finished"' in raw and "behavior_dry_run_valid_001" in raw,
        5.0,
    ):
        raise RuntimeError("valid plan did not reach finished state")

    before = len(node.statuses)
    publish(node, "{bad json")
    if not wait_for_status(node, before, 5.0):
        raise RuntimeError("malformed plan produced no /robot_behavior/status")
    if not wait_for_match(
        node,
        lambda raw: '"state":"fallback"' in raw and "malformed JSON" in raw,
        5.0,
    ):
        raise RuntimeError("malformed plan did not reach fallback state")
    print("BEHAVIOR_DRY_RUN_SMOKE_PASS", flush=True)
finally:
    node.destroy_node()
    rclpy.shutdown()
PY

echo "LOG_START"
tail -120 "$LOG_PATH"
echo "LOG_END"
