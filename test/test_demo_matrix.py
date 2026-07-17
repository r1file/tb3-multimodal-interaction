import copy
from pathlib import Path

import pytest

from tb3_multimodal_interaction.demo_matrix import (
    DemoMatrixError,
    evaluate_result,
    load_matrix,
    select_scenarios,
    validate_matrix,
)


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "config" / "week7_p4_demo_matrix.json"


def test_frozen_matrix_contract_and_coverage():
    matrix = load_matrix(MATRIX)
    assert matrix["schema_version"] == "1.0.0"
    assert len(matrix["scenarios"]) == 14
    assert {item["tier"] for item in matrix["scenarios"]} == {
        "showcase",
        "regression",
        "stress",
    }


def test_matrix_rejects_motion_without_final_stop():
    matrix = load_matrix(MATRIX)
    broken = copy.deepcopy(matrix)
    broken["scenarios"][0]["expected"]["motion_actions"] = ["turn_left"]
    with pytest.raises(DemoMatrixError, match="end in stop"):
        validate_matrix(broken)


def test_text_selection_excludes_camera_rows_by_default():
    matrix = load_matrix(MATRIX)
    selected = select_scenarios(matrix, input_path="text")
    assert selected
    assert all(not item["include_camera"] for item in selected)
    assert {item["scenario_id"] for item in selected} >= {
        "P4-SOC-ZH",
        "P4-MOTION-ZH",
        "P4-B-MANIP-EN",
    }


def test_evaluator_accepts_complete_dry_run_plan():
    scenario = load_matrix(MATRIX)["scenarios"][0]
    result = {
        "published": True,
        "published_plan": {
            "validated": True,
            "reply": "早上好，我们开始吧。",
            "reply_language": "zh",
            "face": "smile",
            "motion": [{"action": "stop", "duration": 0.0}],
        },
        "behavior_statuses": [
            {"state": "finished", "effective_dry_run": True},
        ],
    }
    verdict = evaluate_result(scenario, result)
    assert verdict["status"] == "pass"
    assert not verdict["failures"]


def test_evaluator_rejects_wrong_language_and_motion():
    scenario = load_matrix(MATRIX)["scenarios"][0]
    result = {
        "published": True,
        "published_plan": {
            "validated": True,
            "reply": "Hello",
            "reply_language": "en",
            "face": "smile",
            "motion": [
                {"action": "turn_left", "duration": 0.5},
                {"action": "stop", "duration": 0.0},
            ],
        },
        "behavior_statuses": [{"state": "finished", "effective_dry_run": True}],
    }
    verdict = evaluate_result(scenario, result)
    assert verdict["status"] == "fail"
    assert len(verdict["failures"]) >= 2


def test_boundary_reply_requires_capability_language():
    matrix = load_matrix(MATRIX)
    scenario = next(
        item for item in matrix["scenarios"] if item["scenario_id"] == "P4-B-MANIP-EN"
    )
    result = {
        "published": True,
        "published_plan": {
            "validated": True,
            "reply": "Sure, I will do that now.",
            "reply_language": "en",
            "face": "thinking",
            "motion": [{"action": "stop", "duration": 0.0}],
        },
        "behavior_statuses": [{"state": "finished", "effective_dry_run": True}],
    }
    verdict = evaluate_result(scenario, result)
    assert verdict["status"] == "fail"
    assert any("manipulation" in item for item in verdict["failures"])


def test_camera_row_requires_transported_image():
    matrix = load_matrix(MATRIX)
    scenario = next(
        item for item in matrix["scenarios"] if item["scenario_id"] == "P4-VIS-ZH"
    )
    result = {
        "published": True,
        "ai_terminal": {"image_bytes": 0},
        "published_plan": {
            "validated": True,
            "reply": "我看不清这个物体。",
            "reply_language": "zh",
            "face": "thinking",
            "motion": [{"action": "stop", "duration": 0.0}],
        },
        "behavior_statuses": [{"state": "finished", "effective_dry_run": True}],
    }
    verdict = evaluate_result(scenario, result)
    assert verdict["status"] == "fail"
    assert "camera row used zero image bytes" in verdict["failures"]
