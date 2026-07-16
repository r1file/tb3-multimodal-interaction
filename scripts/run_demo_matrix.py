#!/usr/bin/env python3
"""Run selected official-demo rows on the live ROS graph in dry-run mode."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from tb3_multimodal_interaction.demo_matrix import (
    evaluate_result,
    load_matrix,
    select_scenarios,
)


class DemoRunner(Node):
    def __init__(self) -> None:
        super().__init__("official_demo_matrix_runner")
        self.request_pub = self.create_publisher(String, "/robot_ai/response_request", 10)
        self.asr_pub = self.create_publisher(String, "/robot_asr/text", 10)
        self.statuses: list[dict[str, Any]] = []
        self.plans: list[dict[str, Any]] = []
        self.behavior: list[dict[str, Any]] = []
        self.create_subscription(String, "/robot_ai/status", self._on_status, 50)
        self.create_subscription(String, "/robot_behavior/plan", self._on_plan, 50)
        self.create_subscription(String, "/robot_behavior/status", self._on_behavior, 50)

    @staticmethod
    def _decode(raw: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(raw)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _on_status(self, msg: String) -> None:
        payload = self._decode(msg.data)
        if payload:
            self.statuses.append(payload)

    def _on_plan(self, msg: String) -> None:
        payload = self._decode(msg.data)
        if payload:
            self.plans.append(payload)

    def _on_behavior(self, msg: String) -> None:
        payload = self._decode(msg.data)
        if payload:
            self.behavior.append(payload)

    def wait_until(self, predicate, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if predicate():
                return True
        return False

    @staticmethod
    def _trace(payload: dict[str, Any]) -> str:
        return str(
            payload.get("trace_id")
            or payload.get("request_id")
            or payload.get("input_id")
            or ""
        )

    def _records_for(self, records: list[dict[str, Any]], trace_id: str) -> list[dict[str, Any]]:
        return [item for item in records if self._trace(item) == trace_id]

    def wait_for_graph(self, input_path: str, timeout_s: float) -> bool:
        def ready() -> bool:
            base = self.request_pub.get_subscription_count() > 0
            if input_path.startswith("asr_"):
                base = base and self.asr_pub.get_subscription_count() > 0
            return base

        return self.wait_until(ready, timeout_s)

    def run_scenario(
        self,
        scenario: dict[str, Any],
        *,
        input_path: str,
        run_id: str,
        timeout_s: float,
    ) -> dict[str, Any]:
        scenario_id = scenario["scenario_id"]
        stamp = int(time.time() * 1000)
        trace_id = f"p4_{scenario_id.lower().replace('-', '_')}_{stamp}"
        context_session = f"p4:{run_id}:{scenario_id}:{stamp}"

        injected_asr = input_path.startswith("asr_")
        include_camera = "camera" in input_path
        if injected_asr:
            asr_msg = String()
            asr_msg.data = scenario["text"]
            self.asr_pub.publish(asr_msg)
            self.wait_until(lambda: True, 0.25)

        request = {
            "request_id": trace_id,
            "trace_id": trace_id,
            "scenario_id": scenario_id,
            "trial_id": trace_id,
            "source": "week7_p4_demo_matrix",
            "mode": "dry_run",
            "context_session": context_session,
            "text": "" if injected_asr else scenario["text"],
            "record": False,
            "include_asr": injected_asr,
            "include_camera": include_camera,
            "time": time.time(),
        }
        msg = String()
        msg.data = json.dumps(request, ensure_ascii=False, separators=(",", ":"))
        started = time.monotonic()
        self.request_pub.publish(msg)

        published = self.wait_until(
            lambda: any(
                self._trace(item) == trace_id
                and item.get("state") in {"published", "fallback"}
                for item in self.statuses
            ),
            timeout_s,
        )
        self.wait_until(
            lambda: any(self._trace(item) == trace_id for item in self.plans),
            5.0,
        )
        self.wait_until(
            lambda: any(
                self._trace(item) == trace_id and item.get("state") == "finished"
                for item in self.behavior
            ),
            20.0,
        )

        statuses = self._records_for(self.statuses, trace_id)
        plans = self._records_for(self.plans, trace_id)
        behavior = self._records_for(self.behavior, trace_id)
        result: dict[str, Any] = {
            "matrix_schema_version": "1.0.0",
            "run_id": run_id,
            "scenario_id": scenario_id,
            "tier": scenario["tier"],
            "category": scenario["category"],
            "input_path": input_path,
            "trace_id": trace_id,
            "context_session": context_session,
            "effective_mode": "dry_run",
            "published": bool(published),
            "elapsed_wall_ms": int((time.monotonic() - started) * 1000),
            "ai_terminal": next(
                (
                    item
                    for item in reversed(statuses)
                    if item.get("state") in {"published", "fallback"}
                ),
                {},
            ),
            "published_plan": plans[-1] if plans else {},
            "behavior_statuses": behavior,
        }
        result["verdict"] = evaluate_result(scenario, result)
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--input-path",
        choices=("text", "text_camera", "asr_injected", "asr_camera_injected"),
        default="text",
    )
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--tier", action="append", choices=("showcase", "regression", "stress"), default=[])
    parser.add_argument("--allow-camera", action="store_true")
    parser.add_argument("--timeout-sec", type=float, default=90.0)
    parser.add_argument("--case-gap-sec", type=float, default=0.75)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    matrix = load_matrix(args.matrix)
    matrix_path = {
        "asr_injected": "asr",
        "asr_camera_injected": "asr_camera",
    }.get(args.input_path, args.input_path)
    selected = select_scenarios(
        matrix,
        input_path=matrix_path,
        scenario_ids=set(args.scenario) or None,
        tiers=set(args.tier) or None,
        allow_camera=args.allow_camera,
    )
    if args.validate_only:
        print(
            f"DEMO_MATRIX_VALID scenarios={len(matrix['scenarios'])} selected={len(selected)}",
            flush=True,
        )
        return 0
    if not selected:
        raise RuntimeError("no scenarios selected; camera rows require --allow-camera")

    run_id = args.run_id or f"week7_p4_{args.input_path}_{int(time.time())}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = DemoRunner()
    failed = 0
    warned = 0
    try:
        if not node.wait_for_graph(args.input_path, 12.0):
            raise RuntimeError("ROS graph is not ready for the selected input path")
        with args.output.open("w", encoding="utf-8") as handle:
            for index, scenario in enumerate(selected, start=1):
                print(
                    f"RUN {index}/{len(selected)} {scenario['scenario_id']} {args.input_path}",
                    flush=True,
                )
                result = node.run_scenario(
                    scenario,
                    input_path=args.input_path,
                    run_id=run_id,
                    timeout_s=args.timeout_sec,
                )
                handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                status = result["verdict"]["status"]
                failed += int(status == "fail")
                warned += int(status == "warn")
                print(
                    f"RESULT {scenario['scenario_id']} {status} trace={result['trace_id']}",
                    flush=True,
                )
                gap_end = time.monotonic() + max(0.0, args.case_gap_sec)
                while time.monotonic() < gap_end:
                    rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    print(
        f"DEMO_MATRIX_RUN_COMPLETE run_id={run_id} total={len(selected)} "
        f"fail={failed} warn={warned} pass={len(selected) - failed - warned}",
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
