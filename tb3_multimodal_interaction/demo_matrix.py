"""Validation and deterministic checks for the official demo matrix."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TIERS = {"showcase", "regression", "stress"}
PATHS = {"text", "text_camera", "asr", "asr_camera"}
BOUNDARY_TERMS = {
    "live_fact": {
        "zh": ("无法", "不能", "实时", "最新", "查不到", "获取"),
        "ja": ("できません", "確認できません", "最新", "リアルタイム", "アクセス"),
        "en": ("cannot", "can't", "unable", "live", "current"),
    },
    "manipulation": {
        "zh": ("无法", "不能", "拿", "机械臂"),
        "ja": ("できません", "持", "アーム"),
        "en": ("cannot", "can't", "unable", "pick up", "arm"),
    },
    "autonomous_navigation": {
        "zh": ("无法", "不能", "导航", "建图"),
        "ja": ("できません", "ナビゲーション", "地図"),
        "en": ("cannot", "can't", "navigation", "mapping"),
    },
    "move_then_observe": {
        "zh": ("无法", "不能", "移动后", "新画面"),
        "ja": ("できません", "移動してから", "新しい画像", "一度"),
        "en": ("cannot", "can't", "move then", "new image", "single turn"),
    },
    "visual_uncertainty": {
        "zh": ("看不清", "无法", "不能", "不确定"),
        "ja": ("読めません", "見えません", "不明"),
        "en": ("cannot read", "can't read", "unclear", "not sure"),
    },
}


class DemoMatrixError(ValueError):
    """Raised when a matrix does not satisfy the frozen contract."""


def load_matrix(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_matrix(payload)
    return payload


def validate_matrix(matrix: Any) -> None:
    if not isinstance(matrix, dict):
        raise DemoMatrixError("matrix root must be an object")
    if matrix.get("schema_name") != "tb3_official_demo_matrix":
        raise DemoMatrixError("unexpected schema_name")
    if matrix.get("schema_version") != "1.0.0":
        raise DemoMatrixError("unexpected schema_version")
    scenarios = matrix.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise DemoMatrixError("scenarios must be a non-empty array")

    ids: set[str] = set()
    categories: set[str] = set()
    languages: set[str] = set()
    tiers: set[str] = set()
    for index, scenario in enumerate(scenarios):
        prefix = f"scenarios[{index}]"
        if not isinstance(scenario, dict):
            raise DemoMatrixError(f"{prefix} must be an object")
        scenario_id = str(scenario.get("scenario_id", ""))
        if not scenario_id or scenario_id in ids:
            raise DemoMatrixError(f"{prefix}.scenario_id is empty or duplicated")
        ids.add(scenario_id)
        tier = scenario.get("tier")
        if tier not in TIERS:
            raise DemoMatrixError(f"{scenario_id}: invalid tier {tier!r}")
        tiers.add(str(tier))
        category = str(scenario.get("category", ""))
        categories.add(category)
        language = str(scenario.get("language", ""))
        if language not in {"zh", "ja", "en"}:
            raise DemoMatrixError(f"{scenario_id}: invalid language {language!r}")
        languages.add(language)
        paths = scenario.get("paths")
        if not isinstance(paths, list) or not paths or not set(paths).issubset(PATHS):
            raise DemoMatrixError(f"{scenario_id}: invalid paths")
        expected = scenario.get("expected")
        if not isinstance(expected, dict):
            raise DemoMatrixError(f"{scenario_id}: expected must be an object")
        if expected.get("reply_language") != language:
            raise DemoMatrixError(f"{scenario_id}: expected language mismatch")
        motion = expected.get("motion_actions")
        if not isinstance(motion, list) or not motion or motion[-1] != "stop":
            raise DemoMatrixError(f"{scenario_id}: expected motion must end in stop")
        for field in ("allowed_faces", "fallback_behavior"):
            if not expected.get(field):
                raise DemoMatrixError(f"{scenario_id}: missing expected.{field}")
        for field in ("manual_checks", "warn_if", "fail_if"):
            value = scenario.get(field)
            if not isinstance(value, list) or not value:
                raise DemoMatrixError(f"{scenario_id}: {field} must be non-empty")

    required_categories = {
        "social",
        "visual_qa",
        "ocr",
        "safe_motion",
        "stop_cancel",
        "capability_boundary",
    }
    if not required_categories.issubset(categories):
        raise DemoMatrixError("matrix does not cover every required category")
    if languages != {"zh", "ja", "en"}:
        raise DemoMatrixError("matrix must cover zh, ja, and en")
    if not {"showcase", "regression"}.issubset(tiers):
        raise DemoMatrixError("matrix must separate showcase and regression tiers")


def motion_actions(plan: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for item in plan.get("motion", []):
        if isinstance(item, dict):
            actions.append(str(item.get("action", "")))
    return actions


def _boundary_supported(reply: str, language: str, kind: str) -> bool:
    terms = BOUNDARY_TERMS.get(kind, {}).get(language, ())
    lower = reply.lower()
    return any(term.lower() in lower for term in terms)


def _states(records: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("state", "")) for item in records if isinstance(item, dict)}


def evaluate_result(scenario: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate machine-checkable fields; physical truth remains manual."""
    plan = result.get("published_plan")
    if not isinstance(plan, dict):
        plan = {}
    expected = scenario["expected"]
    failures: list[str] = []
    warnings: list[str] = []

    if not result.get("published"):
        failures.append("AI did not reach published/fallback terminal state")
    if plan.get("reply_language") != expected["reply_language"]:
        failures.append(
            f"reply_language={plan.get('reply_language')!r}, expected={expected['reply_language']!r}"
        )
    reply = str(plan.get("reply", "") or "")
    if not reply.strip():
        failures.append("reply is empty")
    face = str(plan.get("face", "") or "")
    if face not in expected["allowed_faces"]:
        warnings.append(f"face={face!r} outside preferred set {expected['allowed_faces']}")
    actual_motion = motion_actions(plan)
    if actual_motion != expected["motion_actions"]:
        failures.append(
            f"motion={actual_motion!r}, expected={expected['motion_actions']!r}"
        )
    if not actual_motion or actual_motion[-1] != "stop":
        failures.append("final motion is not stop")
    if plan.get("validated") is not True:
        failures.append("published plan is not validator-approved")

    boundary_kind = str(expected.get("boundary_kind", ""))
    if boundary_kind and not _boundary_supported(reply, scenario["language"], boundary_kind):
        failures.append(f"reply does not express {boundary_kind} boundary/uncertainty")
    if boundary_kind == "live_fact" and contains_current_fact_claim(reply):
        failures.append("reply appears to state an unsupported current weather fact")

    if scenario.get("include_camera"):
        ai_terminal = result.get("ai_terminal")
        if not isinstance(ai_terminal, dict):
            ai_terminal = {}
        try:
            image_bytes = int(ai_terminal.get("image_bytes", 0) or 0)
        except (TypeError, ValueError):
            image_bytes = 0
        if image_bytes <= 0:
            failures.append("camera row used zero image bytes")

    behavior_states = _states(result.get("behavior_statuses", []))
    if "finished" not in behavior_states:
        failures.append("behavior did not reach finished")
    terminal = next(
        (
            item
            for item in reversed(result.get("behavior_statuses", []))
            if isinstance(item, dict) and item.get("state") == "finished"
        ),
        {},
    )
    if terminal and terminal.get("effective_dry_run") is not True:
        failures.append("automated demo run was not effective_dry_run=true")

    if scenario.get("requires_physical_scene"):
        warnings.append("physical-scene truth requires manual review")
    if scenario.get("requires_real_motion"):
        warnings.append("real-motion acceptance remains pending after dry-run")

    status = "fail" if failures else "warn" if warnings else "pass"
    return {
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "manual_checks": scenario.get("manual_checks", []),
    }


def select_scenarios(
    matrix: dict[str, Any],
    *,
    input_path: str,
    scenario_ids: set[str] | None = None,
    tiers: set[str] | None = None,
    allow_camera: bool = False,
) -> list[dict[str, Any]]:
    if input_path not in PATHS:
        raise DemoMatrixError(f"invalid input path {input_path!r}")
    selected = []
    for scenario in matrix["scenarios"]:
        if input_path not in scenario["paths"]:
            continue
        if scenario_ids and scenario["scenario_id"] not in scenario_ids:
            continue
        if tiers and scenario["tier"] not in tiers:
            continue
        if scenario.get("include_camera") and not allow_camera:
            continue
        selected.append(scenario)
    return selected


def contains_current_fact_claim(reply: str) -> bool:
    """Conservative helper for reports; boundary evaluation remains primary."""
    patterns = (
        r"\b\d{1,2}\s*°",
        r"℃",
        r"晴れ",
        r"晴天",
        r"晴朗",
        r"雨です",
        r"sunny",
        r"raining",
    )
    return any(re.search(pattern, reply, flags=re.IGNORECASE) for pattern in patterns)
