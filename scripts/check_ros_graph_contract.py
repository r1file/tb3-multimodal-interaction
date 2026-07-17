#!/usr/bin/env python3
"""Check the TB3/full ROS endpoint contract from one fresh graph participant."""

from __future__ import annotations

import os
import sys
import time

import rclpy


TB3_ENDPOINTS = (
    ("pub", "/odom"),
    ("sub", "/robot_motion/action_cmd"),
    ("sub", "/robot_expression/trigger"),
    ("sub", "/robot_face/expression"),
    ("pub", "/robot_camera/jpeg"),
    ("pub", "/robot_audio/pcm"),
    ("sub", "/robot_speech/wav"),
)
FULL_ENDPOINTS = (
    ("sub", "/robot_tts/request"),
    ("pub", "/robot_tts/status"),
    ("sub", "/robot_asr/request"),
    ("pub", "/robot_asr/status"),
)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    if mode not in {"tb3", "full"}:
        print("usage: check_ros_graph_contract.py tb3|full", file=sys.stderr)
        return 2
    timeout_s = float(os.environ.get("ROS_GRAPH_HEALTH_TIMEOUT_S", "15"))
    candidates = [
        item.strip() for item in os.environ["TB3_CMD_VEL_CANDIDATES"].split(",")
        if item.strip()
    ]
    endpoints = list(TB3_ENDPOINTS)
    if mode == "full":
        endpoints.extend(FULL_ENDPOINTS)

    rclpy.init()
    node = rclpy.create_node("tb3_graph_contract_probe")
    try:
        deadline = time.monotonic() + timeout_s
        selected_cmd = ""
        counts: dict[tuple[str, str], int] = {}
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.25)
            cmd_counts = {topic: node.count_subscribers(topic) for topic in candidates}
            selected_cmd = max(cmd_counts, key=cmd_counts.get) if cmd_counts else ""
            counts = {
                (kind, topic): (
                    node.count_publishers(topic) if kind == "pub" else node.count_subscribers(topic)
                )
                for kind, topic in endpoints
            }
            if selected_cmd and cmd_counts[selected_cmd] > 0 and all(value > 0 for value in counts.values()):
                break

        failed = False
        cmd_count = node.count_subscribers(selected_cmd) if selected_cmd else 0
        print(f"{'ok' if cmd_count > 0 else 'missing'} cmd_vel_sub {selected_cmd or '-'} {cmd_count}")
        failed |= cmd_count <= 0
        for kind, topic in endpoints:
            count = counts.get((kind, topic), 0)
            print(f"{'ok' if count > 0 else 'missing'} {kind} {topic} {count}")
            failed |= count <= 0
        return 1 if failed else 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
