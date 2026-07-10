#!/usr/bin/env python3
"""Text-only language consistency smoke test."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from tb3_multimodal_interaction.behavior_plan_contract import reply_matches_language


@dataclass
class Case:
    name: str
    text: str
    expected_language: str


class LanguageSmoke(Node):
    def __init__(self, request_topic: str, plan_topic: str):
        super().__init__("language_contract_smoke")
        self.request_topic = request_topic
        self.plan_topic = plan_topic
        self.request_pub = self.create_publisher(String, request_topic, 10)
        self.create_subscription(String, plan_topic, self.on_plan, 10)
        self._plans: list[dict] = []

    def on_plan(self, msg: String):
        try:
            payload = json.loads(msg.data)
            if isinstance(payload, dict):
                self._plans.append(payload)
        except json.JSONDecodeError:
            self._plans.append({"_parse_error": msg.data})

    def publish_request(self, case: Case):
        payload = {
            "request_id": f"lang_smoke_{case.name}_{int(time.time() * 1000)}",
            "source": "language_contract_smoke",
            "mode": "dry_run",
            "text": case.text,
            "include_asr": False,
            "record": False,
            "include_camera": False,
        }
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.request_pub.publish(msg)

    def wait_for_plan(self, previous_count: int, timeout_sec: float):
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if len(self._plans) > previous_count:
                return self._plans[-1]
        return None

    def wait_for_graph(self, timeout_sec: float) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            request_subs = self.request_pub.get_subscription_count()
            plan_pubs = self.count_publishers(self.plan_topic)
            if request_subs > 0 and plan_pubs > 0:
                return True
        return False


def check_plan(case: Case, plan: dict | None) -> tuple[bool, str]:
    if not isinstance(plan, dict):
        return False, "no plan received"
    if plan.get("_parse_error"):
        return False, f"plan parse error: {plan['_parse_error'][:120]}"
    reply = str(plan.get("reply", "") or "")
    reply_language = str(plan.get("reply_language", "") or "")
    if reply_language != case.expected_language:
        return False, f"reply_language={reply_language!r}, expected={case.expected_language!r}"
    if not reply_matches_language(reply, case.expected_language):
        return False, f"reply text does not match {case.expected_language!r}: {reply!r}"
    return True, f"reply_language={reply_language} reply={reply}"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-topic", default="/robot_ai/response_request")
    parser.add_argument("--plan-topic", default="/robot_behavior/plan")
    parser.add_argument("--timeout-sec", type=float, default=30.0)
    parser.add_argument("--case-gap-sec", type=float, default=1.5)
    parser.add_argument("--graph-timeout-sec", type=float, default=10.0)
    args = parser.parse_args(argv)

    cases = [
        Case("zh", "你好，请用中文回答，并保持不动。", "zh"),
        Case("en", "Hello, please answer in English and stay still.", "en"),
    ]

    rclpy.init()
    node = LanguageSmoke(args.request_topic, args.plan_topic)
    try:
        if not node.wait_for_graph(args.graph_timeout_sec):
            print(
                "FAIL graph: no request subscriber or plan publisher discovered",
                flush=True,
            )
            return 1

        ok = True
        for case in cases:
            previous_count = len(node._plans)
            node.publish_request(case)
            plan = node.wait_for_plan(previous_count, args.timeout_sec)
            passed, detail = check_plan(case, plan)
            print(f"{'PASS' if passed else 'FAIL'} {case.name}: {detail}", flush=True)
            if plan is not None:
                print(json.dumps(plan, ensure_ascii=False, separators=(",", ":")), flush=True)
            ok = ok and passed
            gap_end = time.monotonic() + max(0.0, args.case_gap_sec)
            while time.monotonic() < gap_end:
                rclpy.spin_once(node, timeout_sec=0.1)
        return 0 if ok else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
