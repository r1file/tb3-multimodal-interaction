#!/usr/bin/env python3
"""Summarize Week6 VLM fallback, repair, and latency metrics from JSONL logs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                records.append(
                    {
                        "source_path": str(path),
                        "line_number": line_number,
                        "fallback_used": True,
                        "fallback_reason": f"log_parse_error: {exc.msg}",
                        "error": str(exc),
                    }
                )
                continue
            if isinstance(payload, dict):
                payload.setdefault("source_path", str(path))
                payload.setdefault("line_number", line_number)
                records.append(payload)
    return records


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def first_present(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def normalize_reason(reason: Any, errors: Any = None, error: Any = None) -> str:
    parts: list[str] = []
    if isinstance(reason, str) and reason.strip():
        parts.append(reason.strip())
    for item in as_list(errors):
        if isinstance(item, str) and item.strip():
            parts.append(item.strip())
    if isinstance(error, str) and error.strip():
        parts.append(error.strip())
    if not parts:
        return ""

    text = "; ".join(parts).lower()
    if "malformed json" in text or "jsondecodeerror" in text or "log_parse_error" in text:
        return "malformed_json"
    if "missing final stop" in text or "final stop" in text:
        return "missing_final_stop"
    if "missing_or_empty_stop" in text or "motion" in text and "missing" in text:
        return "missing_or_empty_motion"
    if "invalid motion" in text or "unknown motion" in text or ".action" in text:
        return "unknown_motion"
    if "duration" in text and ("outside" in text or "long" in text or "excessive" in text):
        return "long_duration"
    if "invalid face" in text or "unknown face" in text:
        return "unknown_face"
    if "invalid tts_style" in text:
        return "unknown_tts_style"
    if "reply_language" in text or "reply text does not match" in text:
        return "language_mismatch"
    if "empty_text" in text or "empty input" in text:
        return "asr_empty_text"
    if "camera" in text and ("unavailable" in text or "missing" in text):
        return "camera_unavailable"
    if "timeout" in text:
        return "vlm_timeout"
    if "validated must be true" in text:
        return "validated_false"
    if "policy:" in text and "empty asr" in text:
        return "asr_empty_text"
    if "policy:" in text and ("safety" in text or "unsafe" in text):
        return "safety_block"
    if "parse:" in text:
        return "parse_error"
    if "schema:" in text:
        return "schema_error"
    if "safety:" in text:
        return "safety_block"
    return parts[0][:120]


def record_id(record: dict[str, Any]) -> str:
    return str(
        first_present(
            record,
            "trace_id",
            "request_id",
            "input_id",
            "sample_id",
            "id",
        )
        or ""
    )


def published_plan(record: dict[str, Any]) -> dict[str, Any]:
    return as_dict(first_present(record, "published_plan", "final_plan", "plan"))


def raw_plan(record: dict[str, Any]) -> dict[str, Any]:
    return as_dict(first_present(record, "raw_plan", "parsed_json", "parsed"))


def repair_actions(record: dict[str, Any]) -> list[str]:
    plan = published_plan(record)
    raw = raw_plan(record)
    actions: list[str] = []
    motion_repaired = plan.get("motion_repaired")
    if motion_repaired:
        actions.append(str(motion_repaired))

    raw_motion = raw.get("motion")
    if raw_motion is None and isinstance(raw.get("behavior_plan"), dict):
        raw_motion = raw["behavior_plan"].get("motion")
    plan_motion = plan.get("motion")
    if isinstance(raw_motion, list) and isinstance(plan_motion, list) and raw_motion:
        raw_last = raw_motion[-1] if isinstance(raw_motion[-1], dict) else {}
        plan_last = plan_motion[-1] if isinstance(plan_motion[-1], dict) else {}
        if raw_last.get("action") != "stop" and plan_last.get("action") == "stop":
            actions.append("final_stop_appended")
    return sorted(set(actions))


def latency_values(record: dict[str, Any]) -> dict[str, float]:
    timings = as_dict(record.get("timings"))
    values: dict[str, float] = {}
    for out_key, keys in {
        "total_ms": ("total_ms", "latency_ms"),
        "vlm_ms": ("vlm_ms", "vlm_latency_ms", "latency_ms"),
        "validation_ms": ("validation_ms", "validation_latency_ms"),
        "camera_wait_ms": ("camera_wait_ms",),
        "asr_ms": ("asr_ms",),
        "publish_ms": ("publish_ms",),
    }.items():
        for key in keys:
            value = numeric(timings.get(key)) if key in timings else numeric(record.get(key))
            if value is not None:
                values[out_key] = value
                break
    return values


def record_accepted(record: dict[str, Any]) -> bool:
    for key in ("accepted", "validation_ok", "behavior_validation_ok"):
        if key in record:
            return as_bool(record.get(key))
    if "fallback_used" in record:
        return not as_bool(record.get("fallback_used"))
    return False


def record_published(record: dict[str, Any]) -> bool:
    if "published" in record:
        return as_bool(record.get("published"))
    return bool(published_plan(record))


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    fallback_records = [record for record in records if as_bool(record.get("fallback_used"))]
    accepted_records = [record for record in records if record_accepted(record)]
    published_records = [record for record in records if record_published(record)]

    reason_counts: Counter[str] = Counter()
    raw_reason_counts: Counter[str] = Counter()
    repair_counts: Counter[str] = Counter()
    latency_buckets: dict[str, list[float]] = defaultdict(list)
    failed_cases: list[dict[str, Any]] = []

    accepted_after_repair = 0
    unsafe_block = 0
    for record in records:
        for key, value in latency_values(record).items():
            latency_buckets[key].append(value)

        actions = repair_actions(record)
        if actions:
            repair_counts.update(actions)
            if record_accepted(record) and not as_bool(record.get("fallback_used")):
                accepted_after_repair += 1

        reason = str(record.get("fallback_reason", "") or "")
        raw_reason = reason or str(record.get("error", "") or "")
        normalized = normalize_reason(
            reason,
            errors=record.get("errors"),
            error=record.get("error"),
        )
        if normalized:
            raw_reason_counts[raw_reason[:160] or normalized] += 1
        if as_bool(record.get("fallback_used")):
            reason_counts[normalized or "unknown"] += 1
            if (normalized or "").startswith("safety") or normalized in {
                "long_duration",
                "unknown_motion",
                "validated_false",
            }:
                unsafe_block += 1
            failed_cases.append(
                {
                    "id": record_id(record),
                    "reason": normalized or "unknown",
                    "fallback_reason": reason,
                    "error": str(record.get("error", "") or ""),
                    "source_path": record.get("source_path", ""),
                    "line_number": record.get("line_number", ""),
                }
            )

    latency_summary = {}
    for key, values in latency_buckets.items():
        if not values:
            continue
        latency_summary[key] = {
            "count": len(values),
            "min": round(min(values), 3),
            "median": round(median(values), 3),
            "max": round(max(values), 3),
        }

    return {
        "total": total,
        "accepted": len(accepted_records),
        "published": len(published_records),
        "fallback": len(fallback_records),
        "fallback_rate": round(len(fallback_records) / total, 4) if total else 0.0,
        "fallback_by_reason": dict(reason_counts.most_common()),
        "raw_reason_counts": dict(raw_reason_counts.most_common()),
        "repair_actions": dict(repair_counts.most_common()),
        "accepted_after_repair": accepted_after_repair,
        "repair_success_rate": round(accepted_after_repair / total, 4) if total else 0.0,
        "unsafe_block_count": unsafe_block,
        "latency": latency_summary,
        "failed_cases": failed_cases,
    }


def write_markdown(summary: dict[str, Any], output: Path, inputs: list[Path]) -> None:
    lines = [
        "# Week6 Fallback Metrics",
        "",
        "## Inputs",
        "",
    ]
    lines.extend(f"- `{path}`" for path in inputs)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Total records: `{summary['total']}`",
            f"- Accepted: `{summary['accepted']}`",
            f"- Published: `{summary['published']}`",
            f"- Fallback: `{summary['fallback']}`",
            f"- Fallback rate: `{summary['fallback_rate']:.2%}`",
            f"- Accepted after repair: `{summary['accepted_after_repair']}`",
            f"- Repair success rate: `{summary['repair_success_rate']:.2%}`",
            f"- Unsafe block count: `{summary['unsafe_block_count']}`",
            "",
            "## Fallback By Reason",
            "",
        ]
    )
    if summary["fallback_by_reason"]:
        lines.extend(f"- `{key}`: `{value}`" for key, value in summary["fallback_by_reason"].items())
    else:
        lines.append("- None")

    lines.extend(["", "## Repair Actions", ""])
    if summary["repair_actions"]:
        lines.extend(f"- `{key}`: `{value}`" for key, value in summary["repair_actions"].items())
    else:
        lines.append("- None")

    lines.extend(["", "## Latency", ""])
    if summary["latency"]:
        for key, values in summary["latency"].items():
            lines.append(
                f"- `{key}`: count `{values['count']}`, median `{values['median']}`, "
                f"min `{values['min']}`, max `{values['max']}`"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Failed Cases", ""])
    if summary["failed_cases"]:
        for item in summary["failed_cases"][:50]:
            lines.append(
                f"- `{item['id'] or 'unknown'}`: `{item['reason']}` "
                f"({item['source_path']}:{item['line_number']})"
            )
    else:
        lines.append("- None")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", nargs="+", type=Path, help="Input VLM JSONL log(s).")
    parser.add_argument("--summary-json", type=Path, help="Write summary JSON.")
    parser.add_argument("--markdown", type=Path, help="Write Markdown report.")
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    for path in args.jsonl:
        records.extend(load_jsonl(path))

    summary = summarize(records)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, args.markdown, args.jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
