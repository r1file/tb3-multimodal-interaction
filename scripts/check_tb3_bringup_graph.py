#!/usr/bin/env python3
"""Check the two ROS graph endpoints that prove TB3 bringup is usable."""

import sys
import time

import rclpy


def main():
    timeout_s = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    rclpy.init()
    node = rclpy.create_node("tb3_bringup_readiness_probe")
    try:
        deadline = time.monotonic() + timeout_s
        cmd_subscribers = 0
        odom_publishers = 0
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.25)
            cmd_subscribers = node.count_subscribers("/cmd_vel")
            odom_publishers = node.count_publishers("/odom")
            if cmd_subscribers > 0 and odom_publishers > 0:
                break
        print(f"{cmd_subscribers} {odom_publishers}")
        return 0 if cmd_subscribers > 0 and odom_publishers > 0 else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
