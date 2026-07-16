"""Versioned, research-neutral records for single-turn evaluation."""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from typing import Any


SCHEMA_NAME = "tb3_single_turn_evaluation"
SCHEMA_VERSION = "1.0.0"

# Keep this order stable: JSON may evolve freely within the version, while CSV
# consumers depend on a deterministic header.
CSV_FIELDS = [
    "schema_name",
    "schema_version",
    "record_type",
    "scenario_id",
    "trial_id",
    "trace_id",
    "request_id",
    "session_id",
    "started_at_unix_s",
    "completed_at_unix_s",
    "language",
    "input_source",
    "text",
    "image_bytes",
    "model",
    "mode",
    "asr_status",
    "asr_duration_ms",
    "vlm_status",
    "vlm_duration_ms",
    "validation_status",
    "validation_duration_ms",
    "tts_status",
    "tts_duration_ms",
    "playback_status",
    "playback_duration_ms",
    "execution_status",
    "execution_duration_ms",
    "total_duration_ms",
    "fallback_used",
    "fallback_reason",
    "repair_action",
    "motion_summary",
    "final_status",
    "error_category",
    "raw_model_output",
    "validated_plan",
    "executor_status",
    "tts_status_detail",
    "playback_status_detail",
    "source_artifact",
]


NULLABLE_FIELDS = {
    "scenario_id",
    "trial_id",
    "completed_at_unix_s",
    "image_bytes",
    "asr_status",
    "asr_duration_ms",
    "vlm_duration_ms",
    "validation_duration_ms",
    "tts_status",
    "tts_duration_ms",
    "playback_status",
    "playback_duration_ms",
    "execution_status",
    "execution_duration_ms",
    "total_duration_ms",
    "fallback_reason",
    "repair_action",
    "error_category",
    "raw_model_output",
    "validated_plan",
    "executor_status",
    "tts_status_detail",
    "playback_status_detail",
    "source_artifact",
}

BEHAVIOR_TERMINAL = {"finished", "error", "cancelled"}
TTS_TERMINAL = {"done", "bad_request", "empty_text", "busy"}
PLAYBACK_TERMINAL = {"done", "failed", "error", "ignored"}


def optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def infer_input_source(text_source: str, image_bytes: int | None) -> str:
    source = str(text_source or "").lower()
    has_image = bool(image_bytes)
    if source.startswith("asr"):
        return "asr_camera" if has_image else "asr"
    if source in {"explicit", "fallback_prompt"}:
        return "text_camera" if has_image else "text"
    return "unknown"


def summarize_motion(plan: Any) -> str:
    if not isinstance(plan, dict) or not isinstance(plan.get("motion"), list):
        return ""
    parts = []
    for item in plan["motion"]:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action", "unknown"))
        duration = item.get("duration")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            parts.append(f"{action}:{float(duration):g}s")
        else:
            parts.append(action)
    return ">".join(parts)


def summarize_repairs(plan: Any) -> str | None:
    if not isinstance(plan, dict):
        return None
    values = []
    for key in ("motion_repaired", "motion_override", "policy_override"):
        value = optional_text(plan.get(key))
        if value:
            values.append(f"{key}={value}")
    return ";".join(values) or None


def asr_status_from_text_source(text_source: str) -> str | None:
    source = str(text_source or "").lower()
    if source == "explicit":
        return None
    if source in {"asr_record", "asr_cached"}:
        return "success"
    if source == "asr_timeout":
        return "timeout"
    if source == "fallback_prompt":
        return "missing"
    return None


def make_vlm_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert the VLM-complete event to a canonical, still-pending record."""
    plan = copy.deepcopy(payload.get("published_plan"))
    image_bytes = optional_int(payload.get("image_bytes"))
    text_source = str(payload.get("text_source", "") or "")
    asr_status = asr_status_from_text_source(text_source)
    error = optional_text(payload.get("error"))
    accepted = bool(payload.get("accepted"))
    fallback_used = bool(payload.get("fallback_used"))
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "record_type": "single_turn",
        "scenario_id": optional_text(payload.get("scenario_id")),
        "trial_id": optional_text(payload.get("trial_id")),
        "trace_id": str(payload.get("trace_id", "") or ""),
        "request_id": str(payload.get("request_id", "") or ""),
        "session_id": str(payload.get("context_session", "") or ""),
        "started_at_unix_s": payload.get("received_time", payload.get("time")),
        "completed_at_unix_s": None,
        "language": str(payload.get("expected_reply_language", "unknown") or "unknown"),
        "input_source": infer_input_source(text_source, image_bytes),
        "text": str(payload.get("text", "") or ""),
        "image_bytes": image_bytes,
        "model": str(payload.get("model", "") or ""),
        "mode": str(payload.get("mode", "run") or "run"),
        "asr_status": asr_status,
        "asr_duration_ms": optional_int(payload.get("asr_ms")) if asr_status is not None else None,
        "vlm_status": "error" if error else "success",
        "vlm_duration_ms": optional_int(payload.get("vlm_latency_ms")),
        "validation_status": "accepted" if accepted else "fallback",
        "validation_duration_ms": optional_int(payload.get("validation_latency_ms")),
        "tts_status": None,
        "tts_duration_ms": None,
        "playback_status": None,
        "playback_duration_ms": None,
        "execution_status": None,
        "execution_duration_ms": None,
        "total_duration_ms": None,
        "fallback_used": fallback_used,
        "fallback_reason": optional_text(payload.get("fallback_reason")),
        "repair_action": summarize_repairs(plan),
        "motion_summary": summarize_motion(plan),
        "final_status": "pending",
        "error_category": "vlm_transport_error" if error else None,
        "raw_model_output": payload.get("raw_output"),
        "validated_plan": plan,
        "executor_status": None,
        "tts_status_detail": None,
        "playback_status_detail": None,
        "source_artifact": optional_text(payload.get("source_artifact")),
        "_vlm_total_duration_ms": optional_int(payload.get("total_ms")) or 0,
    }


def json_safe_csv_row(record: dict[str, Any]) -> dict[str, Any]:
    row = {}
    for field_name in CSV_FIELDS:
        value = record.get(field_name)
        if value is None:
            value = ""
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        row[field_name] = value
    return row


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(record.get(key)) for key in CSV_FIELDS}


def _state(payload: dict[str, Any]) -> str:
    return str(payload.get("state", "") or "").strip().lower()


def _trace_id(payload: dict[str, Any]) -> str:
    return str(payload.get("trace_id", payload.get("input_id", "")) or "").strip()


@dataclass
class _PendingTrace:
    record: dict[str, Any] | None = None
    last_received_mono: float = 0.0
    base_received_mono: float | None = None
    behavior: dict[str, Any] | None = None
    tts: dict[str, Any] | None = None
    playback: dict[str, Any] | None = None


@dataclass
class TraceAccumulator:
    """Join cross-node stage events by trace ID and emit one terminal row."""

    timeout_sec: float = 90.0
    _pending: dict[str, _PendingTrace] = field(default_factory=dict)
    _completed: set[str] = field(default_factory=set)

    def add_vlm(self, payload: dict[str, Any], received_mono: float | None = None) -> dict[str, Any] | None:
        trace_id = _trace_id(payload)
        if not trace_id or trace_id in self._completed:
            return None
        now = time.monotonic() if received_mono is None else received_mono
        item = self._pending.setdefault(trace_id, _PendingTrace())
        item.record = make_vlm_record(payload)
        item.base_received_mono = now
        item.last_received_mono = now
        self._apply_cached(item)
        return self._finish_if_ready(trace_id, now)

    def add_behavior(self, payload: dict[str, Any], received_mono: float | None = None) -> dict[str, Any] | None:
        return self._add_stage("behavior", payload, received_mono)

    def add_tts(self, payload: dict[str, Any], received_mono: float | None = None) -> dict[str, Any] | None:
        return self._add_stage("tts", payload, received_mono)

    def add_playback(self, payload: dict[str, Any], received_mono: float | None = None) -> dict[str, Any] | None:
        return self._add_stage("playback", payload, received_mono)

    def _add_stage(self, stage: str, payload: dict[str, Any], received_mono: float | None) -> dict[str, Any] | None:
        trace_id = _trace_id(payload)
        if not trace_id or trace_id in self._completed:
            return None
        now = time.monotonic() if received_mono is None else received_mono
        item = self._pending.setdefault(trace_id, _PendingTrace())
        setattr(item, stage, copy.deepcopy(payload))
        item.last_received_mono = now
        if item.record is not None:
            self._apply_stage(item.record, stage, payload)
        return self._finish_if_ready(trace_id, now)

    def _apply_cached(self, item: _PendingTrace) -> None:
        assert item.record is not None
        for stage in ("behavior", "tts", "playback"):
            payload = getattr(item, stage)
            if payload:
                self._apply_stage(item.record, stage, payload)

    def _apply_stage(self, record: dict[str, Any], stage: str, payload: dict[str, Any]) -> None:
        state = _state(payload)
        if stage == "behavior":
            record["executor_status"] = copy.deepcopy(payload)
            if state in BEHAVIOR_TERMINAL:
                record["execution_status"] = "success" if state == "finished" else state
                record["execution_duration_ms"] = optional_int(payload.get("latency_ms"))
        elif stage == "tts":
            record["tts_status_detail"] = copy.deepcopy(payload)
            ok = bool(payload.get("ok"))
            terminal = state in TTS_TERMINAL or (state and not ok and state not in {"synthesizing", "loading_model"})
            if terminal:
                record["tts_status"] = "success" if state == "done" and ok else state or "error"
                record["tts_duration_ms"] = optional_int(payload.get("latency_ms"))
        elif stage == "playback":
            record["playback_status_detail"] = copy.deepcopy(payload)
            if state in PLAYBACK_TERMINAL:
                record["playback_status"] = "success" if state == "done" and payload.get("ok", True) else state
                record["playback_duration_ms"] = optional_int(payload.get("latency_ms"))

    def _ready(self, record: dict[str, Any]) -> bool:
        if record.get("mode") == "dry_run" or bool((record.get("executor_status") or {}).get("effective_dry_run")):
            return record.get("execution_status") is not None
        if record.get("execution_status") is None or record.get("tts_status") is None:
            return False
        if record.get("tts_status") != "success":
            return True
        return record.get("playback_status") is not None

    def _finish_if_ready(self, trace_id: str, now: float) -> dict[str, Any] | None:
        item = self._pending.get(trace_id)
        if not item or item.record is None or not self._ready(item.record):
            return None
        return self._finish(trace_id, now, timed_out=False)

    def expire(self, received_mono: float | None = None) -> list[dict[str, Any]]:
        now = time.monotonic() if received_mono is None else received_mono
        expired = []
        for trace_id, item in list(self._pending.items()):
            if item.record is None or now - item.last_received_mono < self.timeout_sec:
                continue
            expired.append(self._finish(trace_id, now, timed_out=True))
        return [record for record in expired if record is not None]

    def _finish(self, trace_id: str, now: float, timed_out: bool) -> dict[str, Any] | None:
        item = self._pending.pop(trace_id, None)
        if not item or item.record is None:
            return None
        record = item.record
        if record.get("mode") == "dry_run" or bool((record.get("executor_status") or {}).get("effective_dry_run")):
            record["tts_status"] = record.get("tts_status") or "not_applicable"
            record["playback_status"] = record.get("playback_status") or "not_applicable"
        record["completed_at_unix_s"] = time.time()
        continuation_ms = 0
        if item.base_received_mono is not None:
            continuation_ms = max(0, int((now - item.base_received_mono) * 1000))
        record["total_duration_ms"] = int(record.pop("_vlm_total_duration_ms", 0)) + continuation_ms
        self._classify(record, timed_out)
        self._completed.add(trace_id)
        return public_record(record)

    def _classify(self, record: dict[str, Any], timed_out: bool) -> None:
        if timed_out:
            record["final_status"] = "incomplete"
            record["error_category"] = record.get("error_category") or "incomplete_pipeline"
            return
        failed_stages = {
            "execution_error": record.get("execution_status") in {"error", "cancelled"},
            "tts_error": record.get("tts_status") not in {"success", "not_applicable"},
            "playback_error": record.get("playback_status") not in {"success", "not_applicable"},
        }
        for category, failed in failed_stages.items():
            if failed:
                record["final_status"] = "error"
                record["error_category"] = category
                return
        if record.get("fallback_used"):
            record["final_status"] = "fallback"
            record["error_category"] = record.get("error_category") or "validation_fallback"
        elif record.get("asr_status") in {"timeout", "missing", "error", "no_audio"}:
            record["final_status"] = "degraded"
            record["error_category"] = "asr_instability"
        elif record.get("vlm_status") == "error":
            record["final_status"] = "error"
            record["error_category"] = "vlm_transport_error"
        else:
            record["final_status"] = "success"
