#!/usr/bin/env python3
"""Convert legacy VLM-only JSONL to schema v1 without touching the source."""

import argparse
import csv
import json
from pathlib import Path

from tb3_multimodal_interaction.evaluation_schema import (
    CSV_FIELDS,
    json_safe_csv_row,
    make_vlm_record,
    public_record,
)


def convert(source: Path, jsonl_output: Path, csv_output: Path) -> int:
    jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with source.open(encoding="utf-8") as input_handle, jsonl_output.open(
        "w", encoding="utf-8"
    ) as jsonl_handle, csv_output.open("w", encoding="utf-8", newline="") as csv_handle:
        writer = csv.DictWriter(csv_handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for line_number, line in enumerate(input_handle, 1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"{source}:{line_number}: root must be an object")
            payload["source_artifact"] = str(source)
            record = make_vlm_record(payload)
            record["completed_at_unix_s"] = payload.get("time")
            record["total_duration_ms"] = payload.get("total_ms")
            record.pop("_vlm_total_duration_ms", None)
            if record["fallback_used"]:
                record["final_status"] = "fallback"
                record["error_category"] = "validation_fallback"
            else:
                # The historical file ends at plan publication. Do not silently
                # promote it to a full-chain success without downstream evidence.
                record["final_status"] = "incomplete"
                record["error_category"] = "downstream_status_unavailable"
            public = public_record(record)
            jsonl_handle.write(json.dumps(public, ensure_ascii=False, separators=(",", ":")) + "\n")
            writer.writerow(json_safe_csv_row(public))
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--jsonl-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    args = parser.parse_args()
    count = convert(args.source, args.jsonl_output, args.csv_output)
    print(f"converted {count} records from {args.source}")


if __name__ == "__main__":
    main()
