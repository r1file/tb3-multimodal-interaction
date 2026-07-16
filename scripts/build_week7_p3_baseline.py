#!/usr/bin/env python3
"""Build the Week7 baseline from the preserved Week6 2B/8B summary."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


FIELDS = [
    "model_label",
    "attempt_records",
    "successful_rows",
    "warning_rows",
    "failed_rows",
    "missing_rows",
    "fallback_attempts",
    "fallback_rate",
    "major_error_categories",
    "median_asr_ms",
    "median_vlm_ms",
    "median_total_ms",
]


def error_categories(row_summaries, model_label):
    counts = Counter()
    for row in row_summaries:
        if row.get("model_label") != model_label:
            continue
        verdict = str(row.get("best_verdict", ""))
        notes = str(row.get("notes", "") or "").lower()
        if verdict == "missing":
            counts["missing_trial"] += 1
        if verdict == "fail":
            counts["scenario_failure"] += 1
        if "raw output missing contract fields" in notes:
            counts["model_contract_error"] += 1
        if "requires live-frame review" in notes:
            counts["visual_evidence_uncertain"] += 1
        if "passed after retry" in notes:
            counts["retry_required"] += 1
    return ";".join(f"{name}:{count}" for name, count in sorted(counts.items())) or "none"


def build(source):
    rows = []
    summaries = source.get("row_summaries", [])
    for overall in source.get("overall", []):
        counts = overall.get("row_best_counts", {})
        rows.append(
            {
                "model_label": overall.get("model_label", ""),
                "attempt_records": overall.get("attempt_records", 0),
                "successful_rows": counts.get("pass", 0),
                "warning_rows": counts.get("warn", 0),
                "failed_rows": counts.get("fail", 0),
                "missing_rows": counts.get("missing", 0),
                "fallback_attempts": overall.get("fallback_attempts", 0),
                "fallback_rate": overall.get("fallback_rate", 0),
                "major_error_categories": error_categories(summaries, overall.get("model_label")),
                "median_asr_ms": overall.get("median_asr_ms"),
                "median_vlm_ms": overall.get("median_vlm_ms"),
                "median_total_ms": overall.get("median_total_ms"),
            }
        )
    return rows


def write_outputs(rows, source_path, csv_path, json_path, markdown_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(
            {
                "schema_name": "tb3_week7_p3_baseline",
                "schema_version": "1.0.0",
                "source_artifact": str(source_path),
                "rows": rows,
                "limitations": [
                    "Historical VLM JSONL ends at plan publication.",
                    "ASR failures remain counted in attempted/fallback/error totals.",
                    "Week6 visual-review labels are retained rather than reclassified.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Week7 P3 current-platform baseline",
        "",
        f"Source: `{source_path}` (preserved; not modified).",
        "",
        "| Model | Attempts | Success / warn / fail / missing rows | Fallback | Major error categories | Median ASR / VLM / total ms |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for row in rows:
        outcomes = "/".join(
            str(row[key]) for key in ("successful_rows", "warning_rows", "failed_rows", "missing_rows")
        )
        fallback = f"{row['fallback_attempts']} ({float(row['fallback_rate']):.1%})"
        latency = f"{row['median_asr_ms']} / {row['median_vlm_ms']} / {row['median_total_ms']}"
        lines.append(
            f"| {row['model_label']} | {row['attempt_records']} | {outcomes} | {fallback} | "
            f"{row['major_error_categories']} | {latency} |"
        )
    lines += [
        "",
        "ASR-related failures and fallback attempts remain in the denominator. Historical records lack trace-linked execution/TTS/playback status, so they are not promoted to full-chain success by the v1 converter.",
    ]
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-prefix", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    rows = build(source)
    prefix = args.output_prefix
    write_outputs(
        rows,
        args.source,
        prefix.with_suffix(".csv"),
        prefix.with_suffix(".json"),
        prefix.with_suffix(".md"),
    )
    print(f"wrote {len(rows)} baseline rows to {prefix}.[csv|json|md]")


if __name__ == "__main__":
    main()
