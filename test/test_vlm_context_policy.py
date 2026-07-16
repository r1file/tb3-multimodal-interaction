from tb3_multimodal_interaction.vlm_behavior_client_node import (
    context_relevance_reason,
    is_autonomous_navigation_request,
    is_mixed_motion_visual_request,
    make_policy_override_plan,
)


def test_temporal_object_followup_uses_context():
    assert (
        context_relevance_reason("刚才那个物品是什么？请只回答物品名称。", {})
        == "meta_context"
    )


def test_fresh_visual_question_does_not_use_context():
    assert context_relevance_reason("看一下最新画面，这是什么？", {}) == ""


def test_explicit_correction_uses_context():
    assert context_relevance_reason("不是水杯，是手机。", {}) == "correction"


def test_japanese_move_then_observe_is_capability_boundary():
    text = "右に動いてから新しい画像を見て、何があるか教えてください。"
    assert is_mixed_motion_visual_request(text)
    plan = make_policy_override_plan(text, "trace-ja", "ja")
    assert plan["policy_override"] == "multi_stage_observation_limit"
    assert plan["motion"] == [{"action": "stop", "duration": 0.0}]
    assert "できません" in plan["reply"]


def test_autonomous_navigation_is_deterministic_boundary():
    text = "请自主导航到走廊尽头并建立地图。"
    assert is_autonomous_navigation_request(text)
    plan = make_policy_override_plan(text, "trace-nav", "zh")
    assert plan["policy_override"] == "autonomous_navigation_limit"
    assert plan["motion"] == [{"action": "stop", "duration": 0.0}]
    assert "不能" in plan["reply"]
