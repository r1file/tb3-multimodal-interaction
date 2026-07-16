from tb3_multimodal_interaction.vlm_behavior_client_node import context_relevance_reason


def test_temporal_object_followup_uses_context():
    assert (
        context_relevance_reason("刚才那个物品是什么？请只回答物品名称。", {})
        == "meta_context"
    )


def test_fresh_visual_question_does_not_use_context():
    assert context_relevance_reason("看一下最新画面，这是什么？", {}) == ""


def test_explicit_correction_uses_context():
    assert context_relevance_reason("不是水杯，是手机。", {}) == "correction"
