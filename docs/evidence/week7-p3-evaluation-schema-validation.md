# Week7 P3 evaluation schema validation

Date: 2026-07-16

## Result

P3 is accepted on the current three-machine platform. New single-turn artifacts use `tb3_single_turn_evaluation` schema `1.0.0`, and a Week8-style report can consume one terminal row per `trace_id` without manually matching VLM, executor, TTS, and playback logs.

## Live trace validation

Full-chain no-motion trace `week7_p3_live_001`:

| Field | Observed value |
|---|---|
| Scenario / trial | `P3_TRACE_LINK` / `live_001` |
| Input | text-only, English, no camera |
| Model | `qwen3vl8b` |
| VLM / validation | `success` / `accepted` |
| Execution / TTS / playback | `success` / `success` / `success` |
| Motion | `stop:0s` |
| Repair | `motion_override=stop_only_question` |
| VLM / TTS / playback duration | `4880 / 8936 / 2421 ms` |
| Total monotonic duration | `16346 ms` |
| Final status | `success` |

The same `trace_id` is present in `raw_model_output`, `validated_plan`, `executor_status`, `tts_status_detail`, and `playback_status_detail`. The test temporarily used `dry_run=false` with an explicit no-motion instruction, then restored the TB3 behavior executor to `dry_run=true`.

Nullable dry-run trace `week7_p3_live_002` confirmed:

- `input_source=text`
- `asr_status=null`, `asr_duration_ms=null`
- `tts_status=not_applicable`, `tts_duration_ms=null`
- `playback_status=not_applicable`, `playback_duration_ms=null`
- `execution_status=success`, `final_status=success`

## Artifacts

- Runtime JSONL: `/workspace/runtime_logs/tb3_multimodal_interaction/evaluation/single_turn_v1.jsonl` inside the Server PC ROS container.
- Runtime CSV: `/workspace/runtime_logs/tb3_multimodal_interaction/evaluation/single_turn_v1.csv` inside the Server PC ROS container.
- Contract: `docs/evaluation-schema.md`.
- Historical converter: `scripts/standardize_legacy_vlm_jsonl.py` (writes new output and never modifies input).
- Baseline generator: `scripts/build_week7_p3_baseline.py`.
- Preserved-source baseline: `docs/evidence/week7-p3-baseline.{md,json,csv}`.

## Historical baseline

| Model | Attempts | Pass / warn / fail / missing rows | Fallback | Median ASR / VLM / total ms |
|---|---:|---:|---:|---:|
| 2B full demo postfix | 27 | 16 / 1 / 3 / 3 | 1 (3.7%) | 5411 / 1332 / 6747 |
| 8B full demo user run | 32 | 20 / 1 / 2 / 0 | 6 (18.8%) | 5411 / 3306.5 / 8741 |

The baseline retains failures, missing trials, fallback attempts, contract errors, retry requirements, and uncertain visual evidence. Historical VLM JSONL ends at plan publication, so the v1 converter marks accepted legacy rows as `incomplete/downstream_status_unavailable` rather than claiming downstream success.

## Verification

- Server ROS container: `6 passed` for `test/test_evaluation_schema.py`.
- Local direct pure-function tests: `6 passed`.
- Python compilation passed for modified nodes and scripts.
- `git diff --check` passed.
- AI Max, Server PC, and TB3 lifecycle status returned `ready` after deployment; the evaluation logger appeared exactly once on the Server ROS graph.

## Limitation policy

ASR timeout, missing audio, and ASR errors remain explicit records. A completed downstream turn is classified as `degraded/asr_instability`; an incomplete trace remains `incomplete`. No failed ASR trial is silently removed from the denominator.
