# Single-turn evaluation schema v1

Schema name: `tb3_single_turn_evaluation`
Schema version: `1.0.0`

The Server PC writes one terminal JSONL row and one matching CSV row per `trace_id` to:

- `/workspace/runtime_logs/tb3_multimodal_interaction/evaluation/single_turn_v1.jsonl`
- `/workspace/runtime_logs/tb3_multimodal_interaction/evaluation/single_turn_v1.csv`

The schema describes observable pipeline stages and does not assume SSAM, asynchronous response generation, or any particular model architecture.

## Identity and inputs

| Field | Type | Nullable | Meaning |
|---|---|---:|---|
| `schema_name`, `schema_version`, `record_type` | string | no | Artifact contract metadata. |
| `scenario_id`, `trial_id` | string | yes | Evaluation labels supplied by the caller. |
| `trace_id` | string | no | Cross-machine join key for model, plan, execution, TTS, and playback. |
| `request_id`, `session_id` | string | no | Request and conversational session identifiers. |
| `started_at_unix_s`, `completed_at_unix_s` | number | completion only | Wall-clock labels for correlation; never used to calculate cross-machine duration. |
| `language` | string | no | Expected response language. |
| `input_source` | enum | no | `text`, `text_camera`, `asr`, `asr_camera`, or `unknown`. |
| `text`, `image_bytes`, `model`, `mode` | mixed | image only | Resolved input text, optional image size, model label, and run mode. |

## Stages and outcome

Each stage has a status and a nullable monotonic duration in milliseconds:

- `asr_status`, `asr_duration_ms`
- `vlm_status`, `vlm_duration_ms`
- `validation_status`, `validation_duration_ms`
- `tts_status`, `tts_duration_ms`
- `playback_status`, `playback_duration_ms`
- `execution_status`, `execution_duration_ms`
- `total_duration_ms`

`total_duration_ms` combines the VLM client's request-to-plan monotonic duration with the evaluation logger's local monotonic plan-to-terminal duration. It never subtracts TB3, Server PC, and AI Max wall clocks.

Text-only records set ASR fields to `null`; runs without a camera set `image_bytes` to `null` or `0`; dry-run execution sets TTS and playback status to `not_applicable`. JSON uses `null`; CSV uses an empty cell for the same value.

Outcome fields are `fallback_used`, `fallback_reason`, `repair_action`, `motion_summary`, `final_status`, and `error_category`. Terminal `final_status` values are:

- `success`: all applicable downstream stages completed.
- `degraded`: the turn completed but measured ASR input was missing or unstable.
- `fallback`: the validated fallback plan completed.
- `error`: execution, TTS, playback, or VLM transport failed.
- `incomplete`: a required trace-linked terminal event was not observed before timeout.

ASR timeout/no-audio records remain in the dataset as `degraded` or `error`; they are never silently excluded from denominators.

## Trace evidence

`raw_model_output`, `validated_plan`, `executor_status`, `tts_status_detail`, and `playback_status_detail` preserve the stage evidence used to classify the row. Structured values remain JSON objects in JSONL and are compact JSON strings in CSV.

The TTS adapter publishes speech metadata before audio synthesis, and the TB3 speech player includes that metadata in playback status. This preserves `trace_id` across the existing `UInt8MultiArray` WAV transport without changing the audio payload.

## Legacy data

`scripts/standardize_legacy_vlm_jsonl.py` creates new v1 JSONL/CSV files and never overwrites its source. Because historical VLM logs end at plan publication, accepted legacy rows are classified as `incomplete/downstream_status_unavailable` rather than claimed as full-chain success. The preserved Week6 outcome summary is converted into the Week7 baseline by `scripts/build_week7_p3_baseline.py`.
