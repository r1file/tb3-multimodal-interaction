"""Week5 behavior-plan validation and output mapping helpers."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any


FACE_WHITELIST = {
    "neutral",
    "smile",
    "happy",
    "sad",
    "surprised",
    "concerned",
    "comforting",
    "thinking",
}

MOTION_WHITELIST = {
    "move_forward_slow",
    "move_backward",
    "turn_left",
    "turn_right",
    "stop",
    "look_around",
}

TTS_STYLE_WHITELIST = {
    "calm",
    "gentle",
    "cheerful",
    "neutral",
    "encouraging",
    "soft",
}

LANGUAGE_WHITELIST = {"zh", "ja", "en", "unknown"}

MAX_DURATION_S = 1.5
DEFAULT_FALLBACK_LANGUAGE = "ja"
FALLBACK_REPLIES = {
    "zh": "抱歉，我没有理解清楚。请再说一遍。",
    "ja": "すみません、うまく理解できませんでした。もう一度お願いします。",
    "en": "Sorry, I did not understand clearly. Please try again.",
    "unknown": "すみません、うまく理解できませんでした。もう一度お願いします。",
}
FALLBACK_REPLY = FALLBACK_REPLIES[DEFAULT_FALLBACK_LANGUAGE]

FALLBACK_PLAN = {
    "input_id": "",
    "source": "executor_fallback",
    "validated": True,
    "fallback_used": True,
    "reply": FALLBACK_REPLY,
    "reply_language": DEFAULT_FALLBACK_LANGUAGE,
    "emotion": "neutral",
    "tts_style": "calm",
    "face": "neutral",
    "motion": [{"action": "stop", "duration": 0.2}],
}


@dataclass
class PlanDecision:
    accepted: bool
    fallback_used: bool
    fallback_reason: str
    errors: list[str]
    plan: dict[str, Any]
    raw_plan: dict[str, Any] | None

    def to_status(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "accepted": self.accepted,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "errors": self.errors,
            "input_id": self.plan.get("input_id", ""),
            "trace_id": self.plan.get("trace_id", self.plan.get("input_id", "")),
            "source": self.plan.get("source", ""),
            "reply_language": self.plan.get("reply_language", ""),
        }


def parse_behavior_plan(raw: str) -> tuple[dict[str, Any] | None, str]:
    text = (raw or "").strip()
    if not text:
        return None, "empty payload"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON: {exc.msg}"
    if not isinstance(payload, dict):
        return None, "schema: root must be object"
    return payload, ""


def validate_behavior_plan(
    plan: Any,
    max_duration_s: float = MAX_DURATION_S,
    expected_reply_language: str | None = None,
) -> PlanDecision:
    if not isinstance(plan, dict):
        return fallback_decision(
            "schema: root must be object",
            raw_plan=None,
            expected_reply_language=expected_reply_language,
        )

    errors: list[str] = []
    if plan.get("validated") is not True:
        errors.append("safety: validated must be true")

    reply = plan.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        errors.append("schema: reply must be non-empty string")

    reply_language = str(plan.get("reply_language", "") or "").strip().lower()
    if reply_language not in LANGUAGE_WHITELIST:
        errors.append(f"whitelist: invalid reply_language {reply_language!r}")

    expected_reply_language = normalize_language(expected_reply_language, allow_unknown=True)
    if expected_reply_language in {"zh", "ja", "en"} and reply_language != expected_reply_language:
        errors.append(
            "language: reply_language "
            f"{reply_language!r} does not match expected {expected_reply_language!r}"
        )

    policy_override = str(plan.get("policy_override", "") or "")
    allow_mixed_reply_text = policy_override in {
        "visual_reply_quality:ocr_language_mixed",
        "context_summary",
    }
    if (
        isinstance(reply, str)
        and reply.strip()
        and reply_language in {"zh", "ja", "en"}
        and not allow_mixed_reply_text
    ):
        if not reply_matches_language(reply, reply_language):
            errors.append(f"language: reply text does not match {reply_language!r}")

    emotion = plan.get("emotion")
    if not isinstance(emotion, str) or not emotion.strip():
        errors.append("schema: emotion must be non-empty string")

    tts_style = plan.get("tts_style")
    if tts_style not in TTS_STYLE_WHITELIST:
        errors.append(f"whitelist: invalid tts_style {tts_style!r}")

    face = plan.get("face")
    if face not in FACE_WHITELIST:
        errors.append(f"whitelist: invalid face {face!r}")

    motion = plan.get("motion")
    normalized_motion: list[dict[str, Any]] = []
    repaired_motion_reason = ""
    if motion is None or motion == []:
        normalized_motion = [{"action": "stop", "duration": 0.0}]
        repaired_motion_reason = "missing_or_empty_stop"
    elif not isinstance(motion, list):
        errors.append("schema: motion must be non-empty array")
    else:
        for index, item in enumerate(motion):
            if not isinstance(item, dict):
                errors.append(f"schema: motion[{index}] must be object")
                continue
            action = item.get("action")
            if action == "move_forward":
                action = "move_forward_slow"
                repaired_motion_reason = "move_forward_alias"
            duration = item.get("duration")
            item_errors = False
            if action not in MOTION_WHITELIST:
                errors.append(f"whitelist: invalid motion[{index}].action {action!r}")
                item_errors = True
            if not isinstance(duration, (int, float)) or isinstance(duration, bool):
                errors.append(f"schema: motion[{index}].duration must be number")
                item_errors = True
            elif duration < 0 or duration > max_duration_s:
                errors.append(
                    f"safety: motion[{index}].duration {duration} outside 0..{max_duration_s}"
                )
                item_errors = True
            if not item_errors:
                normalized_motion.append({"action": str(action), "duration": float(duration)})

        if len(normalized_motion) == len(motion) and normalized_motion[-1]["action"] != "stop":
            normalized_motion.append({"action": "stop", "duration": 0.0})

    if errors:
        return fallback_decision(
            "; ".join(errors),
            raw_plan=plan,
            errors=errors,
            expected_reply_language=expected_reply_language,
        )

    normalized = copy.deepcopy(plan)
    normalized["reply"] = reply.strip()
    normalized["reply_language"] = reply_language
    normalized["emotion"] = emotion.strip()
    normalized["tts_style"] = tts_style
    normalized["face"] = face
    normalized["motion"] = normalized_motion
    if repaired_motion_reason:
        normalized["motion_repaired"] = repaired_motion_reason
    fallback_used = bool(normalized.get("fallback_used", False))
    normalized["fallback_used"] = fallback_used
    normalized.setdefault("input_id", "")
    normalized.setdefault("trace_id", normalized.get("input_id", ""))
    normalized.setdefault("source", "unknown")

    return PlanDecision(
        accepted=True,
        fallback_used=fallback_used,
        fallback_reason=str(normalized.get("fallback_reason", "") or "") if fallback_used else "",
        errors=[],
        plan=normalized,
        raw_plan=copy.deepcopy(plan),
    )


def fallback_decision(
    reason: str,
    raw_plan: dict[str, Any] | None,
    errors: list[str] | None = None,
    expected_reply_language: str | None = None,
) -> PlanDecision:
    plan = copy.deepcopy(FALLBACK_PLAN)
    fallback_language = choose_fallback_language(raw_plan, expected_reply_language)
    plan["reply_language"] = fallback_language
    plan["reply"] = FALLBACK_REPLIES.get(fallback_language, FALLBACK_REPLY)
    plan["fallback_reason"] = reason
    if isinstance(raw_plan, dict):
        plan["input_id"] = str(raw_plan.get("input_id", "") or "")
        plan["trace_id"] = str(raw_plan.get("trace_id", plan["input_id"]) or plan["input_id"])
        plan["source"] = str(raw_plan.get("source", "executor_fallback") or "executor_fallback")
    return PlanDecision(
        accepted=False,
        fallback_used=True,
        fallback_reason=reason,
        errors=errors or [reason],
        plan=plan,
        raw_plan=copy.deepcopy(raw_plan),
    )


def decide_behavior_plan(
    raw: str,
    max_duration_s: float = MAX_DURATION_S,
    expected_reply_language: str | None = None,
) -> PlanDecision:
    parsed, parse_error = parse_behavior_plan(raw)
    if parsed is None:
        return fallback_decision(
            f"parse: {parse_error}",
            raw_plan=None,
            expected_reply_language=expected_reply_language,
        )
    return validate_behavior_plan(
        parsed,
        max_duration_s=max_duration_s,
        expected_reply_language=expected_reply_language,
    )


def normalize_language(value: str | None, allow_unknown: bool = False) -> str:
    language = str(value or "").strip().lower()
    if language in {"zh", "ja", "en"}:
        return language
    if allow_unknown and language == "unknown":
        return "unknown"
    return ""


def has_kana(text: str) -> bool:
    return any("\u3040" <= char <= "\u30ff" for char in text)


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def has_ascii_letter(text: str) -> bool:
    return any(("a" <= char <= "z") or ("A" <= char <= "Z") for char in text)


def detect_text_language(text: str, default: str = "unknown") -> str:
    value = str(text or "")
    if has_kana(value):
        return "ja"
    if has_cjk(value):
        return "zh"
    if has_ascii_letter(value):
        return "en"
    fallback = normalize_language(default, allow_unknown=True)
    return fallback or "unknown"


def reply_matches_language(reply: str, reply_language: str) -> bool:
    language = normalize_language(reply_language, allow_unknown=True)
    if language == "unknown":
        return True
    if language == "zh":
        return has_cjk(reply) and not has_kana(reply)
    if language == "ja":
        return has_kana(reply)
    if language == "en":
        return has_ascii_letter(reply) and not has_cjk(reply) and not has_kana(reply)
    return False


def choose_fallback_language(
    raw_plan: dict[str, Any] | None,
    expected_reply_language: str | None = None,
) -> str:
    expected = normalize_language(expected_reply_language, allow_unknown=False)
    if expected:
        return expected
    if isinstance(raw_plan, dict):
        raw_language = normalize_language(raw_plan.get("reply_language"), allow_unknown=False)
        if raw_language:
            return raw_language
    return DEFAULT_FALLBACK_LANGUAGE


def infer_language(text: str, default: str = "ja") -> str:
    return detect_text_language(text, default=default)


def make_tts_request(plan: dict[str, Any], default_language: str = "ja") -> dict[str, Any]:
    text = str(plan.get("reply", "")).strip()
    reply_language = normalize_language(plan.get("reply_language"), allow_unknown=False)
    return {
        "text": text,
        "language": reply_language or infer_language(text, default_language),
        "style": str(plan.get("tts_style", "calm")),
        "input_id": str(plan.get("input_id", "")),
        "trace_id": str(plan.get("trace_id", plan.get("input_id", ""))),
        "source": str(plan.get("source", "")),
    }


def make_motion_command(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": str(item.get("action", "stop")),
        "duration": float(item.get("duration", 0.0)),
    }
