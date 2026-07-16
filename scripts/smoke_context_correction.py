#!/usr/bin/env python3
"""Run the Week 7 correction-memory acceptance test on the live ROS graph."""

import argparse
import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CorrectionSmoke(Node):
    def __init__(self):
        super().__init__("week7_context_correction_smoke")
        self.request_pub = self.create_publisher(String, "/robot_ai/response_request", 10)
        self.ai_statuses = {}
        self.plans = {}
        self.behavior_statuses = {}
        self.tts_statuses = {}
        self.speech_events = []
        self.create_subscription(String, "/robot_ai/status", self.on_ai_status, 10)
        self.create_subscription(String, "/robot_behavior/plan", self.on_plan, 10)
        self.create_subscription(String, "/robot_behavior/status", self.on_behavior_status, 10)
        self.create_subscription(String, "/robot_tts/status", self.on_tts_status, 10)
        self.create_subscription(String, "/robot_speech/status", self.on_speech_status, 10)

    @staticmethod
    def parse_payload(raw):
        try:
            payload = json.loads(raw)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def trace_id(payload):
        return str(
            payload.get("trace_id")
            or payload.get("request_id")
            or payload.get("input_id")
            or ""
        )

    def store(self, target, raw):
        payload = self.parse_payload(raw)
        if not payload:
            return
        trace_id = self.trace_id(payload)
        if trace_id:
            target.setdefault(trace_id, []).append(payload)

    def on_ai_status(self, msg):
        self.store(self.ai_statuses, msg.data)

    def on_plan(self, msg):
        payload = self.parse_payload(msg.data)
        if not payload:
            return
        trace_id = self.trace_id(payload)
        if trace_id:
            self.plans[trace_id] = payload

    def on_behavior_status(self, msg):
        self.store(self.behavior_statuses, msg.data)

    def on_tts_status(self, msg):
        self.store(self.tts_statuses, msg.data)

    def on_speech_status(self, msg):
        self.speech_events.append(msg.data)

    def wait_until(self, predicate, timeout_s, description):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if predicate():
                return
        raise RuntimeError(f"timeout waiting for {description}")

    @staticmethod
    def find_state(records, trace_id, state):
        return next(
            (item for item in reversed(records.get(trace_id, [])) if item.get("state") == state),
            None,
        )

    def publish_turn(self, trace_id, session, text, timeout_s):
        payload = {
            "request_id": trace_id,
            "trace_id": trace_id,
            "scenario_id": "W7-P0-CORRECTION",
            "trial_id": trace_id,
            "source": "week7_correction_smoke",
            "mode": "dry_run",
            "context_session": session,
            "text": text,
            "record": False,
            "include_asr": False,
            "include_camera": False,
            "time": time.time(),
        }
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.request_pub.publish(msg)

        self.wait_until(
            lambda: self.find_state(self.ai_statuses, trace_id, "published") is not None,
            timeout_s,
            f"AI published for {trace_id}",
        )
        self.wait_until(
            lambda: trace_id in self.plans,
            5.0,
            f"behavior plan for {trace_id}",
        )
        self.wait_until(
            lambda: self.find_state(self.behavior_statuses, trace_id, "finished") is not None,
            15.0,
            f"behavior finished for {trace_id}",
        )

        ai = self.find_state(self.ai_statuses, trace_id, "published")
        behavior = self.find_state(self.behavior_statuses, trace_id, "finished")
        tts_request = self.find_state(self.behavior_statuses, trace_id, "tts_request")
        face_publish = self.find_state(self.behavior_statuses, trace_id, "face_publish")
        final_stop = self.find_state(self.behavior_statuses, trace_id, "final_stop")
        plan = self.plans[trace_id]
        if not ai.get("accepted") or ai.get("fallback_used"):
            raise RuntimeError(f"AI validation failed for {trace_id}: {ai}")
        if plan.get("fallback_used"):
            raise RuntimeError(f"fallback plan for {trace_id}: {plan}")
        if not behavior.get("effective_dry_run"):
            raise RuntimeError(f"behavior was not dry-run for {trace_id}: {behavior}")
        if not all((tts_request, face_publish, final_stop)):
            raise RuntimeError(f"incomplete dry-run dispatch states for {trace_id}")

        return {
            "trace_id": trace_id,
            "text": text,
            "reply": plan.get("reply", ""),
            "plan_source": plan.get("source", ""),
            "motion": plan.get("motion", []),
            "accepted": ai.get("accepted"),
            "fallback_used": ai.get("fallback_used"),
            "context_turns": ai.get("context_turns"),
            "context_used_reason": ai.get("context_used_reason"),
            "timings": ai.get("timings", {}),
            "behavior_state": behavior.get("state"),
            "effective_dry_run": behavior.get("effective_dry_run"),
            "dispatch_states": ["tts_request", "face_publish", "final_stop", "finished"],
            "physical_outputs": "skipped_by_effective_dry_run",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--session", default="")
    args = parser.parse_args()

    session = args.session or f"week7_p0_correction_{int(time.time())}"
    stamp = int(time.time())
    turns = (
        (f"week7_p0_baseline_{stamp}", "请记住：这个物品是水杯。请只回答水杯两个字。"),
        (f"week7_p0_correction_{stamp}", "不是水杯，是手机。请更正并只回答手机两个字。"),
        (f"week7_p0_followup_{stamp}", "刚才那个物品是什么？请只回答物品名称。"),
    )

    rclpy.init()
    node = CorrectionSmoke()
    try:
        node.wait_until(
            lambda: node.request_pub.get_subscription_count() > 0,
            10.0,
            "/robot_ai/response_request subscriber",
        )
        results = []
        for trace_id, text in turns:
            results.append(node.publish_turn(trace_id, session, text, args.timeout))
            time.sleep(0.5)

        if "水杯" not in results[0]["reply"]:
            raise RuntimeError(f"baseline did not establish 水杯: {results[0]['reply']}")
        if "手机" not in results[1]["reply"]:
            raise RuntimeError(f"correction did not establish 手机: {results[1]['reply']}")
        if results[1]["context_used_reason"] != "correction":
            raise RuntimeError(f"correction context was not selected: {results[1]}")
        if int(results[1]["context_turns"] or 0) < 1:
            raise RuntimeError(f"correction had no prior context: {results[1]}")
        if "手机" not in results[2]["reply"]:
            raise RuntimeError(f"later response did not preserve 手机: {results[2]['reply']}")
        if int(results[2]["context_turns"] or 0) < 1:
            raise RuntimeError(f"follow-up had no correction context: {results[2]}")

        summary = {
            "result": "WEEK7_CONTEXT_CORRECTION_PASS",
            "session": session,
            "turns": results,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
