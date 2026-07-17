from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_asr_preloads_multilingual_model_before_ready():
    source = (ROOT / "tb3_multimodal_interaction" / "asr_topic_adapter_node.py").read_text()
    assert "self.preload_model()" in source
    assert source.index("self.preload_model()") < source.index("ASR adapter ready:")
    assert "'languages': ['zh', 'ja', 'en']" in source
    assert "SPEECH_MODEL_READY_FILE" in source


def test_tts_preloads_and_warms_all_existing_language_pipelines():
    source = (ROOT / "tb3_multimodal_interaction" / "tts_topic_adapter_node.py").read_text()
    assert "self.preload_pipelines()" in source
    assert source.index("self.preload_pipelines()") < source.index("TTS adapter ready:")
    assert "for language in ('ja', 'zh', 'en')" in source
    assert "voice=self.voices[language]" in source
    assert "Kokoro warm-up returned no audio" in source


def test_server_start_waits_for_both_preload_markers():
    compose = (ROOT / "deploy" / "server_pc" / "docker" / "docker-compose.yml").read_text()
    start = (ROOT / "scripts" / "start_server_stack_host.sh").read_text()
    assert compose.count("SPEECH_MODEL_READY_FILE=") == 2
    assert compose.count('rm -f "$$SPEECH_MODEL_READY_FILE"') == 2
    assert 'wait_for_speech_model "$ASR_CONTAINER" "ASR"' in start
    assert 'wait_for_speech_model "$TTS_CONTAINER" "TTS ja/zh/en"' in start
    assert "ROLE_STARTUP_GRACE_S" in start
    status = (ROOT / "deploy" / "role_status.py").read_text()
    assert 'speech_model_state(os.environ["ASR_CONTAINER"])' in status
    assert 'speech_model_state(os.environ["TTS_CONTAINER"])' in status
