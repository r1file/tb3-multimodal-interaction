from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_server_dashboard_replaces_flat_chain_and_node_panels():
    html = (ROOT / "tb3_multimodal_interaction/web/server_control.html").read_text()
    for marker in (
        "Chain Status",
        "Speech Pipeline",
        "node-asr",
        "node-camera",
        "node-vlm",
        "node-validator",
        "node-executor",
        "node-tts",
        "node-playback",
        "latencyBars",
        "request_ingress_ms",
        "asr_capture_ms",
        "model inference only",
        "externalNodes",
    ):
        assert marker in html
    assert "AI Chain Status" not in html


def test_ai_dashboard_has_multimodal_input_and_output_inspectors():
    html = (ROOT / "ai_max_vlm_server/dashboard/index.html").read_text()
    for marker in (
        "AI Input Inspector",
        "inputImage",
        "inputText",
        "User Prompt",
        "Generated JSON",
        "Latest Llama Log",
        "Llama Processes",
    ):
        assert marker in html


def test_llama_process_monitor_has_host_pid_visibility_and_ps_binary():
    run_script = (ROOT / "ai_max_vlm_server/dashboard/run_dashboard.sh").read_text()
    dockerfile = (ROOT / "ai_max_vlm_server/dashboard/Dockerfile").read_text()
    assert "--pid host" in run_script
    assert "procps" in dockerfile


def test_dashboard_topics_include_p3_status_and_input_inspector():
    server = (ROOT / "tb3_multimodal_interaction/server_control_node.py").read_text()
    vlm = (ROOT / "tb3_multimodal_interaction/vlm_behavior_client_node.py").read_text()
    evaluation = (ROOT / "tb3_multimodal_interaction/evaluation_logger_node.py").read_text()
    assert "/robot_ai/input_inspector" in server
    assert "/robot_evaluation/status" in server
    assert "image_jpeg_base64" in vlm
    assert "self.status_pub.publish" in evaluation
