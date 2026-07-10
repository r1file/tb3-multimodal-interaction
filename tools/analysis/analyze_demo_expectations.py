#!/usr/bin/env python3
"""Check Week6 demo logs for accepted-but-bad-reply scenario issues."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


UNCERTAINTY_TERMS = (
    "わかりません",
    "分かりません",
    "確認できません",
    "見られません",
    "できません",
    "不明",
    "不確か",
    "よく見えません",
    "不知道",
    "不确定",
    "无法确认",
    "看不清",
    "I do not know",
    "I don't know",
    "not sure",
    "cannot",
    "can't",
)

EXTERNAL_FACT_PATTERNS = (
    r"晴れ",
    r"雨",
    r"曇",
    r"雪",
    r"sunny",
    r"rain",
    r"cloudy",
    r"snow",
    r"degrees?",
    r"℃",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text or not text.startswith("{"):
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                payload.setdefault("source_path", str(path))
                payload.setdefault("line_number", line_number)
                rows.append(payload)
    return rows


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_of(record: dict[str, Any]) -> str:
    return str(record.get("text", "") or "")


def plan_of(record: dict[str, Any]) -> dict[str, Any]:
    return as_dict(record.get("published_plan")) or as_dict(record.get("raw_plan"))


def trace_id(record: dict[str, Any]) -> str:
    return str(record.get("trace_id") or record.get("request_id") or record.get("input_id") or "")


def reply_of(record: dict[str, Any]) -> str:
    return str(plan_of(record).get("reply") or record.get("reply") or "")


def language_of(record: dict[str, Any]) -> str:
    return str(plan_of(record).get("reply_language") or record.get("reply_language") or "")


def motion_actions(record: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for item in as_list(plan_of(record).get("motion")):
        if isinstance(item, dict):
            actions.append(str(item.get("action", "")))
    return actions


def has_uncertainty(text: str) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in UNCERTAINTY_TERMS)


def mentions_external_fact(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower) for pattern in EXTERNAL_FACT_PATTERNS)


def matches(expectation: dict[str, Any], record: dict[str, Any]) -> bool:
    haystack = text_of(record).lower()
    terms = expectation.get("match_text_contains") or []
    return any(str(term).lower() in haystack for term in terms)


def check_record(expectation: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    reply = reply_of(record)
    actions = motion_actions(record)
    expected_language = expectation.get("expected_reply_language")
    if expected_language and language_of(record) != expected_language:
        issues.append(
            {
                "severity": "fail",
                "kind": "language_mismatch",
                "message": f"expected {expected_language}, got {language_of(record) or 'empty'}",
            }
        )

    allowed_motion = set(expectation.get("allowed_motion") or [])
    if allowed_motion:
        unexpected = [action for action in actions if action and action not in allowed_motion]
        if unexpected:
            issues.append(
                {
                    "severity": "fail",
                    "kind": "unexpected_motion",
                    "message": f"unexpected motion {unexpected}; allowed {sorted(allowed_motion)}",
                }
            )

    if expectation.get("forbid_external_fact") and mentions_external_fact(reply) and not has_uncertainty(reply):
        issues.append(
            {
                "severity": "fail",
                "kind": "unsupported_external_fact",
                "message": "reply states an external fact without uncertainty",
            }
        )

    if expectation.get("should_express_uncertainty") and not has_uncertainty(reply):
        issues.append(
            {
                "severity": "fail",
                "kind": "missing_uncertainty",
                "message": "reply should express uncertainty or inability to check",
            }
        )

    if expectation.get("require_visual_grounding") and reply and not has_uncertainty(reply):
        issues.append(
            {
                "severity": "warn",
                "kind": "needs_visual_review",
                "message": "visual answer accepted; verify image manually if object label matters",
            }
        )

    return issues


def evaluate(expectations: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    matched = 0
    for record in records:
        matched_expectations = [item for item in expectations if matches(item, record)]
        if not matched_expectations:
            continue
        matched += 1
        for expectation in matched_expectations:
            issues = check_record(expectation, record)
            status = "pass"
            if any(issue["severity"] == "fail" for issue in issues):
                status = "fail"
            elif issues:
                status = "warn"
            counts[status] += 1
            for issue in issues:
                counts[issue["kind"]] += 1
            results.append(
                {
                    "status": status,
                    "scenario_id": expectation.get("scenario_id", ""),
                    "trace_id": trace_id(record),
                    "text": text_of(record),
                    "reply": reply_of(record),
                    "reply_language": language_of(record),
                    "motion": motion_actions(record),
                    "issues": issues,
                    "source_path": record.get("source_path", ""),
                    "line_number": record.get("line_number", ""),
                }
            )
    return {
        "records": len(records),
        "matched_records": matched,
        "checks": len(results),
        "counts": dict(counts),
        "results": results,
    }


def write_markdown(summary: dict[str, Any], output: Path) -> None:
    lines = [
        "# Week6 Demo Expectation Check",
        "",
        "## Summary",
        "",
        f"- Records: `{summary['records']}`",
        f"- Matched records: `{summary['matched_records']}`",
        f"- Checks: `{summary['checks']}`",
    ]
    for key, value in sorted(summary["counts"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Results", ""])
    for item in summary["results"]:
        lines.append(
            f"- `{item['status']}` `{item['scenario_id']}` `{item['trace_id']}`: "
            f"{item['text']} -> {item['reply']}"
        )
        for issue in item["issues"]:
            lines.append(f"  - `{issue['severity']}` `{issue['kind']}`: {issue['message']}")
    if not summary["results"]:
        lines.append("- No matching records")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expectations", required=True, type=Path)
    parser.add_argument("--logs", required=True, nargs="+", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    expectations = load_jsonl(args.expectations)
    records: list[dict[str, Any]] = []
    for path in args.logs:
        records.extend(load_jsonl(path))
    summary = evaluate(expectations, records)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, args.markdown)
    return 1 if summary["counts"].get("fail", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
