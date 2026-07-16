"""ROS node that joins single-turn stage events and writes schema v1 artifacts."""

import csv
import json
import time
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from tb3_multimodal_interaction.evaluation_schema import (
    CSV_FIELDS,
    TraceAccumulator,
    json_safe_csv_row,
)


class EvaluationLogger(Node):
    def __init__(self):
        super().__init__("evaluation_logger_node")
        self.declare_parameter("vlm_event_topic", "/robot_evaluation/vlm_complete")
        self.declare_parameter("behavior_status_topic", "/robot_behavior/status")
        self.declare_parameter("tts_status_topic", "/robot_tts/status")
        self.declare_parameter("playback_status_topic", "/robot_speech/status")
        self.declare_parameter("evaluation_status_topic", "/robot_evaluation/status")
        self.declare_parameter("log_dir", "/workspace/runtime_logs/tb3_multimodal_interaction/evaluation")
        self.declare_parameter("trace_timeout_sec", 90.0)

        self.log_dir = Path(str(self.get_parameter("log_dir").value))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.log_dir / "single_turn_v1.jsonl"
        self.csv_path = self.log_dir / "single_turn_v1.csv"
        self.accumulator = TraceAccumulator(float(self.get_parameter("trace_timeout_sec").value))
        self.status_pub = self.create_publisher(
            String,
            str(self.get_parameter("evaluation_status_topic").value),
            10,
        )

        self.create_subscription(
            String,
            str(self.get_parameter("vlm_event_topic").value),
            lambda msg: self.on_event("vlm", msg),
            20,
        )
        self.create_subscription(
            String,
            str(self.get_parameter("behavior_status_topic").value),
            lambda msg: self.on_event("behavior", msg),
            50,
        )
        self.create_subscription(
            String,
            str(self.get_parameter("tts_status_topic").value),
            lambda msg: self.on_event("tts", msg),
            20,
        )
        self.create_subscription(
            String,
            str(self.get_parameter("playback_status_topic").value),
            lambda msg: self.on_event("playback", msg),
            20,
        )
        self.create_timer(1.0, self.flush_expired)
        self.get_logger().info(
            f"Evaluation logger ready: jsonl={self.jsonl_path}, csv={self.csv_path}"
        )

    def on_event(self, source, msg):
        try:
            payload = json.loads(msg.data or "{}")
            if not isinstance(payload, dict):
                raise ValueError("event root must be an object")
        except Exception as exc:
            self.get_logger().warn(f"ignored malformed {source} event: {exc}")
            return
        now = time.monotonic()
        handler = {
            "vlm": self.accumulator.add_vlm,
            "behavior": self.accumulator.add_behavior,
            "tts": self.accumulator.add_tts,
            "playback": self.accumulator.add_playback,
        }[source]
        record = handler(payload, now)
        if record:
            self.write_record(record)

    def flush_expired(self):
        for record in self.accumulator.expire(time.monotonic()):
            self.write_record(record)

    def write_record(self, record):
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        csv_exists = self.csv_path.exists()
        with self.csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            if not csv_exists:
                writer.writeheader()
            writer.writerow(json_safe_csv_row(record))
        status_msg = String()
        status_msg.data = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self.status_pub.publish(status_msg)
        self.get_logger().info(
            f"wrote trace={record['trace_id']} final_status={record['final_status']}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = EvaluationLogger()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
