import json
from pathlib import Path

from tb3_multimodal_interaction.behavior_plan_contract import (
    decide_behavior_plan,
    detect_text_language,
    make_motion_command,
    make_tts_request,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_valid_plan_is_accepted_and_mapped():
    decision = decide_behavior_plan(load_fixture("behavior_plan_valid.json"))

    assert decision.accepted is True
    assert decision.fallback_used is False
    assert decision.plan["input_id"] == "behavior_fixture_valid_001"
    assert decision.plan["motion"][-1]["action"] == "stop"

    tts_request = make_tts_request(decision.plan)
    assert tts_request["text"] == "I see the object. I will stay here."
    assert tts_request["language"] == "en"
    assert tts_request["style"] == "calm"

    motion_command = make_motion_command(decision.plan["motion"][0])
    assert motion_command == {"action": "turn_left", "duration": 0.2}


def test_malformed_plan_uses_fallback_stop():
    decision = decide_behavior_plan(load_fixture("behavior_plan_malformed.txt"))

    assert decision.accepted is False
    assert decision.fallback_used is True
    assert decision.plan["face"] == "neutral"
    assert decision.plan["motion"] == [{"action": "stop", "duration": 0.2}]
    assert "parse:" in decision.fallback_reason


def test_unknown_action_and_long_duration_use_fallback():
    decision = decide_behavior_plan(load_fixture("behavior_plan_unknown_action.json"))

    assert decision.accepted is False
    assert decision.fallback_used is True
    assert decision.plan["motion"] == [{"action": "stop", "duration": 0.2}]
    assert "invalid motion" in decision.fallback_reason
    assert "outside 0..1.5" in decision.fallback_reason


def test_validated_false_uses_fallback_even_if_shape_is_safe():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["validated"] = False

    decision = decide_behavior_plan(json.dumps(payload))

    assert decision.accepted is False
    assert decision.fallback_used is True
    assert decision.plan["input_id"] == "behavior_fixture_valid_001"
    assert "validated must be true" in decision.fallback_reason


def test_safe_motion_missing_final_stop_is_repaired():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["reply"] = "我向前走一点。"
    payload["reply_language"] = "zh"
    payload["motion"] = [{"action": "move_forward_slow", "duration": 0.8}]

    decision = decide_behavior_plan(
        json.dumps(payload, ensure_ascii=False),
        expected_reply_language="zh",
    )

    assert decision.accepted is True
    assert decision.fallback_used is False
    assert decision.plan["motion"] == [
        {"action": "move_forward_slow", "duration": 0.8},
        {"action": "stop", "duration": 0.0},
    ]


def test_missing_motion_is_repaired_to_stop():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["reply"] = "这是一个水杯。"
    payload["reply_language"] = "zh"
    payload.pop("motion")

    decision = decide_behavior_plan(
        json.dumps(payload, ensure_ascii=False),
        expected_reply_language="zh",
    )

    assert decision.accepted is True
    assert decision.fallback_used is False
    assert decision.plan["reply"] == "这是一个水杯。"
    assert decision.plan["motion"] == [{"action": "stop", "duration": 0.0}]
    assert decision.plan["motion_repaired"] == "missing_or_empty_stop"


def test_empty_motion_is_repaired_to_stop():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["motion"] = []

    decision = decide_behavior_plan(json.dumps(payload))

    assert decision.accepted is True
    assert decision.fallback_used is False
    assert decision.plan["motion"] == [{"action": "stop", "duration": 0.0}]


def test_expected_chinese_accepts_chinese_reply():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["reply"] = "我看到了画面，会保持不动。"
    payload["reply_language"] = "zh"
    payload["motion"] = [{"action": "stop", "duration": 0.0}]

    decision = decide_behavior_plan(
        json.dumps(payload, ensure_ascii=False),
        expected_reply_language=detect_text_language("你好，请保持不动。"),
    )

    assert decision.accepted is True
    assert decision.plan["reply_language"] == "zh"
    assert make_tts_request(decision.plan)["language"] == "zh"


def test_expected_chinese_rejects_english_reply():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["reply"] = "I will stay still."
    payload["reply_language"] = "en"
    payload["motion"] = [{"action": "stop", "duration": 0.0}]

    decision = decide_behavior_plan(
        json.dumps(payload),
        expected_reply_language=detect_text_language("你好，请保持不动。"),
    )

    assert decision.accepted is False
    assert decision.plan["reply_language"] == "zh"
    assert "does not match expected 'zh'" in decision.fallback_reason


def test_expected_english_accepts_english_reply():
    payload = json.loads(load_fixture("behavior_plan_valid.json"))
    payload["motion"] = [{"action": "stop", "duration": 0.0}]

    decision = decide_behavior_plan(
        json.dumps(payload),
        expected_reply_language=detect_text_language("Hello, please stay still."),
    )

    assert decision.accepted is True
    assert decision.plan["reply_language"] == "en"
