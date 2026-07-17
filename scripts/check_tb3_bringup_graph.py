#!/usr/bin/env python3
"""Check the two ROS graph endpoints that prove TB3 bringup is usable."""

import os
import sys
import time

import rclpy


def main():
    timeout_s = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    candidates = [
        item.strip() for item in os.environ["TB3_CMD_VEL_CANDIDATES"].split(",")
        if item.strip()
    ]
    if not candidates:
        raise ValueError("TB3_CMD_VEL_CANDIDATES must not be empty")
    rclpy.init()
    node = rclpy.create_node("tb3_bringup_readiness_probe")
    try:
        deadline = time.monotonic() + timeout_s
        cmd_subscribers = 0
        cmd_topic = ""
        odom_publishers = 0
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.25)
            counts = [(topic, node.count_subscribers(topic)) for topic in candidates]
            cmd_topic, cmd_subscribers = max(counts, key=lambda item: item[1])
            odom_publishers = node.count_publishers("/odom")
            if cmd_subscribers > 0 and odom_publishers > 0:
                break
        print(f"{cmd_subscribers} {odom_publishers} {cmd_topic}")
        return 0 if cmd_subscribers > 0 and odom_publishers > 0 else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
