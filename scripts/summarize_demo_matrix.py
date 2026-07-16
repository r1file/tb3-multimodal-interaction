#!/usr/bin/env python3
"""Summarize official-demo JSONL without rewriting the raw result file."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tb3_multimodal_interaction.demo_matrix import load_matrix


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: row must be an object")
        rows.append(payload)
    return rows


def build_summary(matrix: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    scenarios = {item["scenario_id"]: item for item in matrix["scenarios"]}
    counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    results = []
    for row in rows:
        scenario_id = str(row.get("scenario_id", ""))
        input_path = str(row.get("input_path", ""))
        if scenario_id not in scenarios:
            raise ValueError(f"result references unknown scenario {scenario_id!r}")
        status = str((row.get("verdict") or {}).get("status", "fail"))
        counts[status] += 1
        path_counts[input_path] += 1
        seen.add((scenario_id, input_path))
        results.append(
            {
                "scenario_id": scenario_id,
                "tier": scenarios[scenario_id]["tier"],
                "input_path": input_path,
                "status": status,
                "trace_id": row.get("trace_id", ""),
                "failures": (row.get("verdict") or {}).get("failures", []),
                "warnings": (row.get("verdict") or {}).get("warnings", []),
            }
        )

    required_pairs = {
        (item["scenario_id"], path)
        for item in matrix["scenarios"]
        for path in item["paths"]
    }
    pending = sorted(required_pairs - seen)
    return {
        "matrix_schema_version": matrix["schema_version"],
        "scenario_count": len(scenarios),
        "result_count": len(rows),
        "verdict_counts": dict(sorted(counts.items())),
        "path_counts": dict(sorted(path_counts.items())),
        "covered_pairs": len(seen),
        "required_pairs": len(required_pairs),
        "pending_pairs": [
            {"scenario_id": scenario_id, "input_path": input_path}
            for scenario_id, input_path in pending
        ],
        "results": results,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Official demo matrix summary",
        "",
        f"- Matrix scenarios: `{summary['scenario_count']}`",
        f"- Recorded results: `{summary['result_count']}`",
        f"- Covered scenario/path pairs: `{summary['covered_pairs']}/{summary['required_pairs']}`",
        f"- Verdict counts: `{json.dumps(summary['verdict_counts'], sort_keys=True)}`",
        f"- Path counts: `{json.dumps(summary['path_counts'], sort_keys=True)}`",
        "",
        "## Recorded rows",
        "",
        "| Scenario | Tier | Path | Verdict | Trace |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in summary["results"]:
        lines.append(
            f"| {item['scenario_id']} | {item['tier']} | {item['input_path']} | "
            f"{item['status']} | {item['trace_id']} |"
        )
    lines.extend(["", "## Pending scenario/path pairs", ""])
    for item in summary["pending_pairs"]:
        lines.append(f"- `{item['scenario_id']}` via `{item['input_path']}`")
    if not summary["pending_pairs"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--results", required=True, nargs="+", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    matrix = load_matrix(args.matrix)
    rows: list[dict[str, Any]] = []
    for path in args.results:
        rows.extend(load_jsonl(path))
    summary = build_summary(matrix, rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(summary), encoding="utf-8")
    return 1 if summary["verdict_counts"].get("fail", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
