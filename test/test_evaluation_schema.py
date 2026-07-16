from tb3_multimodal_interaction.evaluation_schema import (
    CSV_FIELDS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    TraceAccumulator,
    json_safe_csv_row,
    make_vlm_record,
)


def vlm_event(**overrides):
    event = {
        "received_time": 1000.0,
        "time": 1008.0,
        "request_id": "request-1",
        "trace_id": "trace-1",
        "scenario_id": "S1",
        "trial_id": "trial-1",
        "mode": "run",
        "model": "qwen3vl8b",
        "text": "hello",
        "expected_reply_language": "en",
        "context_session": "ui:run",
        "image_bytes": 1200,
        "text_source": "asr_record",
        "asr_ms": 5100,
        "vlm_latency_ms": 2500,
        "validation_latency_ms": 2,
        "total_ms": 7605,
        "accepted": True,
        "fallback_used": False,
        "fallback_reason": "",
        "raw_output": '{"reply":"hello"}',
        "published_plan": {
            "trace_id": "trace-1",
            "reply": "hello",
            "motion": [{"action": "stop", "duration": 0.0}],
        },
    }
    event.update(overrides)
    return event


def test_vlm_record_has_version_nullable_stages_and_research_neutral_source():
    record = make_vlm_record(vlm_event())
    assert record["schema_name"] == SCHEMA_NAME
    assert record["schema_version"] == SCHEMA_VERSION
    assert record["input_source"] == "asr_camera"
    assert record["tts_status"] is None
    assert record["playback_status"] is None
    assert record["execution_status"] is None

    text_only = make_vlm_record(
        vlm_event(text_source="explicit", asr_ms=0, image_bytes=0)
    )
    assert text_only["input_source"] == "text"
    assert text_only["asr_status"] is None
    assert text_only["asr_duration_ms"] is None

    asr_only = make_vlm_record(vlm_event(image_bytes=0))
    assert asr_only["input_source"] == "asr"


def test_trace_accumulator_joins_out_of_order_events():
    accumulator = TraceAccumulator(timeout_sec=30.0)
    assert accumulator.add_tts(
        {"trace_id": "trace-1", "state": "done", "ok": True, "latency_ms": 800},
        10.0,
    ) is None
    assert accumulator.add_playback(
        {"trace_id": "trace-1", "state": "done", "ok": True, "latency_ms": 1200},
        11.0,
    ) is None
    assert accumulator.add_behavior(
        {"trace_id": "trace-1", "state": "finished", "latency_ms": 300},
        11.5,
    ) is None
    record = accumulator.add_vlm(vlm_event(), 12.0)

    assert record is not None
    assert record["trace_id"] == "trace-1"
    assert record["execution_status"] == "success"
    assert record["tts_status"] == "success"
    assert record["playback_status"] == "success"
    assert record["final_status"] == "success"
    assert record["total_duration_ms"] == 7605


def test_dry_run_marks_tts_and_playback_not_applicable():
    accumulator = TraceAccumulator(timeout_sec=30.0)
    assert accumulator.add_vlm(vlm_event(mode="dry_run"), 10.0) is None
    record = accumulator.add_behavior(
        {
            "trace_id": "trace-1",
            "state": "finished",
            "latency_ms": 20,
            "effective_dry_run": True,
        },
        10.1,
    )
    assert record["tts_status"] == "not_applicable"
    assert record["playback_status"] == "not_applicable"
    assert record["final_status"] == "success"


def test_asr_timeout_is_measured_as_degraded_not_dropped():
    accumulator = TraceAccumulator(timeout_sec=30.0)
    event = vlm_event(text_source="asr_timeout", asr_ms=0)
    assert accumulator.add_vlm(event, 10.0) is None
    assert accumulator.add_behavior(
        {"trace_id": "trace-1", "state": "finished", "latency_ms": 10}, 10.1
    ) is None
    assert accumulator.add_tts(
        {"trace_id": "trace-1", "state": "done", "ok": True, "latency_ms": 10}, 10.2
    ) is None
    record = accumulator.add_playback(
        {"trace_id": "trace-1", "state": "done", "ok": True, "latency_ms": 10}, 10.3
    )
    assert record["asr_status"] == "timeout"
    assert record["final_status"] == "degraded"
    assert record["error_category"] == "asr_instability"


def test_timeout_emits_incomplete_record():
    accumulator = TraceAccumulator(timeout_sec=2.0)
    accumulator.add_vlm(vlm_event(), 10.0)
    assert accumulator.expire(11.9) == []
    records = accumulator.expire(12.0)
    assert len(records) == 1
    assert records[0]["final_status"] == "incomplete"
    assert records[0]["error_category"] == "incomplete_pipeline"


def test_csv_row_has_stable_header_and_empty_nullable_cells():
    record = make_vlm_record(vlm_event(scenario_id=None))
    row = json_safe_csv_row(record)
    assert list(row) == CSV_FIELDS
    assert row["scenario_id"] == ""
    assert row["validated_plan"].startswith("{")
