#!/usr/bin/env python3
"""Run Week6 P5 scenarios through the ASR-text consumption path.

This publishes each scenario text to /robot_asr/text, then sends an AI response
request with no explicit text so vlm_behavior_client_node must consume cached ASR
text. It is deterministic enough for CI-like demo regression without requiring a
person to speak every standard input.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class AsrInjectedRunner(Node):
    def __init__(self, request_topic: str, asr_text_topic: str, status_topic: str, plan_topic: str):
        super().__init__("asr_injected_injected_runner")
        self.asr_pub = self.create_publisher(String, asr_text_topic, 10)
        self.request_pub = self.create_publisher(String, request_topic, 10)
        self.statuses: list[dict[str, Any]] = []
        self.plans: list[dict[str, Any]] = []
        self.create_subscription(String, status_topic, self.on_status, 10)
        self.create_subscription(String, plan_topic, self.on_plan, 10)

    def on_status(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            payload = {"raw": msg.data}
        if isinstance(payload, dict):
            self.statuses.append(payload)

    def on_plan(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            payload = {"raw": msg.data}
        if isinstance(payload, dict):
            self.plans.append(payload)

    def wait_until(self, predicate, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if predicate():
                return True
        return False

    def wait_for_graph(self, timeout_s: float) -> bool:
        return self.wait_until(
            lambda: self.request_pub.get_subscription_count() > 0 and self.asr_pub.get_subscription_count() > 0,
            timeout_s,
        )

    def run_case(self, scenario: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        trace_id = f"asr_injected_{scenario['trial_id']}_{int(time.time() * 1000)}"
        context_session = f"p5_asr:{scenario['trial_id']}"
        start = time.time()

        asr_msg = String()
        asr_msg.data = str(scenario.get("text", ""))
        self.asr_pub.publish(asr_msg)
        self.wait_until(lambda: True, 0.25)

        req = {
            "request_id": trace_id,
            "trace_id": trace_id,
            "source": "asr_injected_injected",
            "mode": "dry_run",
            "text": "",
            "record": False,
            "include_asr": True,
            "include_camera": True,
            "context_session": context_session,
            "time": time.time(),
        }
        msg = String()
        msg.data = json.dumps(req, ensure_ascii=False, separators=(",", ":"))
        self.request_pub.publish(msg)

        def published() -> bool:
            return any(
                item.get("trace_id") == trace_id and item.get("state") in {"published", "fallback"}
                for item in self.statuses
            )

        ok = self.wait_until(published, timeout_s)
        latest_status = next(
            (
                item
                for item in reversed(self.statuses)
                if item.get("trace_id") == trace_id and item.get("state") in {"published", "fallback"}
            ),
            {},
        )
        latest_plan = next((item for item in reversed(self.plans) if item.get("trace_id") == trace_id), {})
        return {
            **scenario,
            "trace_id": trace_id,
            "context_session": context_session,
            "ok": bool(ok),
            "elapsed_wall_ms": int((time.time() - start) * 1000),
            "ai_status": latest_status,
            "published_plan": latest_plan,
        }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text:
            rows.append(json.loads(text))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-sec", type=float, default=90.0)
    parser.add_argument("--request-topic", default="/robot_ai/response_request")
    parser.add_argument("--asr-text-topic", default="/robot_asr/text")
    parser.add_argument("--status-topic", default="/robot_ai/status")
    parser.add_argument("--plan-topic", default="/robot_behavior/plan")
    args = parser.parse_args()

    scenarios = load_jsonl(args.scenarios)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    rclpy.init()
    node = AsrInjectedRunner(args.request_topic, args.asr_text_topic, args.status_topic, args.plan_topic)
    try:
        if not node.wait_for_graph(10.0):
            raise RuntimeError("ROS graph not ready for ASR injected runner")
        with args.output.open("w", encoding="utf-8") as handle:
            for index, scenario in enumerate(scenarios, start=1):
                node.get_logger().info(f"running {index}/{len(scenarios)} {scenario.get('scenario_id')}")
                record = node.run_case(scenario, args.timeout_sec)
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)
                time.sleep(0.5)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
