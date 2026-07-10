#!/usr/bin/env bash
set -eo pipefail

LOG_PATH="${LOG_PATH:-/tmp/behavior_no_motion_hardware.log}"

source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh
set -u

echo "Checking Week2/3 stack before Week5 hardware smoke..."
bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/health_check_full.sh full

rm -f "$LOG_PATH"
pgrep -f "/tb3_multimodal_interaction/behavior_executor_node" | xargs -r kill >/dev/null 2>&1 || true
sleep 1

ros2 run tb3_multimodal_interaction behavior_executor_node --ros-args -p dry_run:=false >"$LOG_PATH" 2>&1 &
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


class HardwareSmokeNode(Node):
    def __init__(self):
        super().__init__("behavior_no_motion_hardware_smoke")
        self.plan_pub = self.create_publisher(String, "/robot_behavior/plan", 10)
        self.behavior = []
        self.tts = []
        self.speech = []
        self.face = []
        self.create_subscription(String, "/robot_behavior/status", self.on_behavior, 10)
        self.create_subscription(String, "/robot_tts/status", self.on_tts, 10)
        self.create_subscription(String, "/robot_speech/status", self.on_speech, 10)
        self.create_subscription(String, "/robot_face/status", self.on_face, 10)

    def on_behavior(self, msg):
        self.behavior.append(msg.data)
        print("BEHAVIOR", msg.data, flush=True)

    def on_tts(self, msg):
        self.tts.append(msg.data)
        print("TTS", msg.data, flush=True)

    def on_speech(self, msg):
        self.speech.append(msg.data)
        print("SPEECH", msg.data, flush=True)

    def on_face(self, msg):
        self.face.append(msg.data)
        print("FACE", msg.data, flush=True)


def spin_until(node, predicate, timeout_s):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if predicate():
            return True
    return False


def has_behavior_state(node, state):
    return any(f'"state":"{state}"' in raw for raw in node.behavior)


def has_stop_only_motion(node):
    motion_lines = [raw for raw in node.behavior if '"state":"motion_start"' in raw]
    return bool(motion_lines) and all('"action":"stop"' in raw for raw in motion_lines)


rclpy.init()
node = HardwareSmokeNode()
try:
    if not spin_until(node, lambda: node.plan_pub.get_subscription_count() > 0, 8.0):
        raise RuntimeError("/robot_behavior/plan has no subscribers")

    plan = {
        "input_id": "behavior_no_motion_hw_001",
        "source": "hardware_smoke",
        "validated": True,
        "fallback_used": False,
        "reply": "Week five no motion hardware smoke. I will stay here.",
        "emotion": "neutral",
        "tts_style": "calm",
        "face": "thinking",
        "motion": [{"action": "stop", "duration": 0.2}],
    }
    msg = String()
    msg.data = json.dumps(plan, separators=(",", ":"))
    node.plan_pub.publish(msg)
    rclpy.spin_once(node, timeout_sec=0.2)

    required = ("received", "accepted", "tts_request", "face_publish", "motion_start", "final_stop", "finished")
    for state in required:
        if not spin_until(node, lambda state=state: has_behavior_state(node, state), 10.0):
            raise RuntimeError(f"missing behavior state {state}")

    if not has_stop_only_motion(node):
        raise RuntimeError("hardware no-motion smoke saw a non-stop motion_start")

    if not spin_until(node, lambda: len(node.face) > 0, 5.0):
        raise RuntimeError("no /robot_face/status observed")

    if not spin_until(node, lambda: len(node.tts) > 0, 25.0):
        raise RuntimeError("no /robot_tts/status observed")

    spin_until(node, lambda: len(node.speech) > 0, 8.0)
    print(
        "BEHAVIOR_NO_MOTION_HARDWARE_SMOKE_PASS "
        f"behavior={len(node.behavior)} tts={len(node.tts)} "
        f"speech={len(node.speech)} face={len(node.face)}",
        flush=True,
    )
finally:
    node.destroy_node()
    rclpy.shutdown()
PY

echo "LOG_START"
tail -160 "$LOG_PATH"
echo "LOG_END"
