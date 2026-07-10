import json
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from tb3_multimodal_interaction.behavior_plan_contract import (
    MAX_DURATION_S,
    decide_behavior_plan,
    make_motion_command,
    make_tts_request,
)


class BehaviorExecutor(Node):
    def __init__(self):
        super().__init__("behavior_executor_node")
        self.declare_parameter("plan_topic", "/robot_behavior/plan")
        self.declare_parameter("status_topic", "/robot_behavior/status")
        self.declare_parameter("tts_topic", "/robot_tts/request")
        self.declare_parameter("face_topic", "/robot_face/expression")
        self.declare_parameter("motion_topic", "/robot_motion/action_cmd")
        self.declare_parameter("dry_run", True)
        self.declare_parameter("motion_gap_sec", 0.08)
        self.declare_parameter("default_language", "ja")
        self.declare_parameter("max_duration", MAX_DURATION_S)

        plan_topic = str(self.get_parameter("plan_topic").value)
        status_topic = str(self.get_parameter("status_topic").value)
        tts_topic = str(self.get_parameter("tts_topic").value)
        face_topic = str(self.get_parameter("face_topic").value)
        motion_topic = str(self.get_parameter("motion_topic").value)

        self.dry_run = bool(self.get_parameter("dry_run").value)
        self.motion_gap_sec = float(self.get_parameter("motion_gap_sec").value)
        self.default_language = str(self.get_parameter("default_language").value)
        self.max_duration = float(self.get_parameter("max_duration").value)

        self.tts_pub = self.create_publisher(String, tts_topic, 10)
        self.face_pub = self.create_publisher(String, face_topic, 10)
        self.motion_pub = self.create_publisher(String, motion_topic, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)
        self.create_subscription(String, plan_topic, self.on_plan, 10)
        self.create_subscription(Bool, "/emergency_stop", self.on_emergency_stop, 10)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker = None
        self.get_logger().info(
            "Behavior executor ready: "
            f"plan={plan_topic}, status={status_topic}, dry_run={self.dry_run}"
        )

    def on_emergency_stop(self, msg):
        if not msg.data:
            return
        self._stop_event.set()
        status = {
            "state": "cancelled",
            "accepted": False,
            "fallback_used": True,
            "fallback_reason": "emergency_stop",
            "errors": ["emergency_stop"],
            "input_id": "",
            "source": "emergency_stop",
        }
        self.publish_status(status)
        self.publish_string(self.motion_pub, json.dumps({"action": "stop", "duration": 0.0}))

    def on_plan(self, msg):
        received_time = time.time()
        received_mono = time.perf_counter()
        decision = decide_behavior_plan(msg.data, max_duration_s=self.max_duration)
        self.publish_status(
            decision.to_status("received"),
            received_time=received_time,
            received_mono=received_mono,
        )
        status_state = "fallback" if decision.fallback_used else "accepted"
        self.publish_status(
            decision.to_status(status_state),
            received_time=received_time,
            received_mono=received_mono,
        )

        with self._lock:
            self._stop_event.set()
            if self._worker and self._worker.is_alive():
                self._worker.join(timeout=0.3)
            self._stop_event.clear()
            self._worker = threading.Thread(
                target=self.execute_plan,
                args=(decision, received_time, received_mono),
                daemon=True,
            )
            self._worker.start()

    def execute_plan(self, decision, received_time, received_mono):
        plan = decision.plan
        effective_dry_run = self.effective_dry_run(plan)
        try:
            self.publish_tts(plan, decision, received_time, received_mono, effective_dry_run)
            self.publish_face(plan, decision, received_time, received_mono, effective_dry_run)
            for index, motion in enumerate(plan.get("motion", [])):
                if self._stop_event.is_set():
                    self.publish_status(
                        {
                            **decision.to_status("cancelled"),
                            "effective_dry_run": effective_dry_run,
                        },
                        received_time=received_time,
                        received_mono=received_mono,
                    )
                    break
                self.publish_motion(motion, index, decision, received_time, received_mono, effective_dry_run)
            self.publish_stop(decision, received_time, received_mono, effective_dry_run)
            self.publish_status(
                {
                    **decision.to_status("finished"),
                    "effective_dry_run": effective_dry_run,
                },
                received_time=received_time,
                received_mono=received_mono,
            )
        except Exception as exc:
            self.get_logger().error(f"Behavior execution error: {exc}")
            self.publish_status(
                {
                    **decision.to_status("error"),
                    "error": f"{type(exc).__name__}: {exc}",
                    "effective_dry_run": effective_dry_run,
                },
                received_time=received_time,
                received_mono=received_mono,
            )
            self.publish_stop(decision, received_time, received_mono, effective_dry_run)

    def effective_dry_run(self, plan):
        mode = str(plan.get("execution_mode", "")).strip().lower()
        if mode == "dry_run":
            return True
        if mode == "run":
            return False
        return self.dry_run

    def publish_tts(self, plan, decision, received_time, received_mono, effective_dry_run):
        payload = make_tts_request(plan, default_language=self.default_language)
        self.publish_status(
            {
                **decision.to_status("tts_request"),
                "topic": "/robot_tts/request",
                "payload": payload,
                "effective_dry_run": effective_dry_run,
            },
            received_time=received_time,
            received_mono=received_mono,
        )
        self.publish_string(
            self.tts_pub,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            effective_dry_run,
        )

    def publish_face(self, plan, decision, received_time, received_mono, effective_dry_run):
        face = str(plan.get("face", "neutral"))
        self.publish_status(
            {
                **decision.to_status("face_publish"),
                "topic": "/robot_face/expression",
                "face": face,
                "effective_dry_run": effective_dry_run,
            },
            received_time=received_time,
            received_mono=received_mono,
        )
        self.publish_string(self.face_pub, face, effective_dry_run)

    def publish_motion(self, motion, index, decision, received_time, received_mono, effective_dry_run):
        payload = make_motion_command(motion)
        self.publish_status(
            {
                **decision.to_status("motion_start"),
                "topic": "/robot_motion/action_cmd",
                "motion_index": index,
                "payload": payload,
                "effective_dry_run": effective_dry_run,
            },
            received_time=received_time,
            received_mono=received_mono,
        )
        self.publish_string(
            self.motion_pub,
            json.dumps(payload, separators=(",", ":")),
            effective_dry_run,
        )
        duration = max(0.0, min(float(payload["duration"]), self.max_duration))
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time and not self._stop_event.is_set():
            remaining = max(0.0, end_time - time.monotonic())
            time.sleep(min(0.05, remaining))
        self.publish_status(
            {
                **decision.to_status("motion_end"),
                "motion_index": index,
                "payload": payload,
                "effective_dry_run": effective_dry_run,
            },
            received_time=received_time,
            received_mono=received_mono,
        )
        if self.motion_gap_sec > 0:
            time.sleep(self.motion_gap_sec)

    def publish_stop(self, decision, received_time, received_mono=None, effective_dry_run=None):
        if effective_dry_run is None:
            effective_dry_run = self.dry_run
        payload = {"action": "stop", "duration": 0.0}
        self.publish_status(
            {
                **decision.to_status("final_stop"),
                "topic": "/robot_motion/action_cmd",
                "payload": payload,
                "effective_dry_run": effective_dry_run,
            },
            received_time=received_time,
            received_mono=received_mono,
        )
        self.publish_string(
            self.motion_pub,
            json.dumps(payload, separators=(",", ":")),
            effective_dry_run,
        )

    def publish_string(self, publisher, value, effective_dry_run=None):
        if effective_dry_run is None:
            effective_dry_run = self.dry_run
        if effective_dry_run:
            self.get_logger().info(f"dry_run publish skipped: {value}")
            return
        msg = String()
        msg.data = value
        publisher.publish(msg)

    def publish_status(self, payload, received_time=None, received_mono=None):
        status = dict(payload)
        status["time"] = time.time()
        if received_time is not None:
            status["received_time"] = received_time
            if received_mono is not None:
                status["latency_ms"] = int((time.perf_counter() - received_mono) * 1000)
            else:
                status["latency_ms"] = int((time.time() - received_time) * 1000)
        status["dry_run"] = self.dry_run
        status.setdefault("effective_dry_run", self.dry_run)
        msg = String()
        msg.data = json.dumps(status, ensure_ascii=False, separators=(",", ":"))
        self.status_pub.publish(msg)
        if status.get("state") in {"fallback", "error"}:
            self.get_logger().warn(msg.data)
        else:
            self.get_logger().info(msg.data)

    def destroy_node(self):
        self._stop_event.set()
        msg = String()
        msg.data = json.dumps({"action": "stop", "duration": 0.0}, separators=(",", ":"))
        if not self.dry_run:
            self.motion_pub.publish(msg)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BehaviorExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
