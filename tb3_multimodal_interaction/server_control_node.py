import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from urllib import request as urlrequest
from urllib.parse import parse_qs

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Week3 Robot Control</title>
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; background: #f4f6f8; color: #172126; font-family: system-ui, sans-serif; }
    main { min-height: 100vh; padding: 18px; display: grid; grid-template-rows: auto 1fr; gap: 14px; }
    header { display: flex; align-items: end; justify-content: space-between; gap: 16px; }
    h1 { margin: 0; font-size: 24px; line-height: 1.2; }
    .subtitle { margin: 4px 0 0; color: #506067; font-size: 13px; }
    .clock { color: #506067; font-size: 13px; text-align: right; }
    .dashboard { display: grid; grid-template-columns: 300px minmax(380px, 1fr) minmax(420px, 0.95fr); gap: 14px; align-items: start; }
    .stack { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
    .panel { background: #fff; border: 1px solid #d3dcdf; border-radius: 8px; padding: 14px; min-width: 0; }
    .panel-title { margin: 0 0 10px; color: #506067; font-size: 12px; font-weight: 850; text-transform: uppercase; }
    .buttons { display: grid; gap: 10px; }
    button { min-height: 44px; border: 1px solid #c8d1d1; border-radius: 8px; background: #fff; color: #172126; font-size: 14px; font-weight: 760; cursor: pointer; }
    button:hover { border-color: #7b8d90; }
    button:active { transform: translateY(1px); background: #ffe08a; }
    .control-btn { text-align: left; padding: 0 14px; }
    .accent { background: #d9eee6; }
    .danger { background: #ffd1c9; }
    .expr-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .status-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .card { border: 1px solid #d7e0e2; border-radius: 8px; padding: 10px; min-width: 0; background: #fbfcfc; }
    .card h3 { margin: 0 0 8px; font-size: 13px; color: #506067; }
    .metric { display: flex; justify-content: space-between; gap: 10px; font-size: 13px; line-height: 1.45; }
    .metric b { color: #172126; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .textbar { min-height: 46px; max-height: 96px; overflow: auto; white-space: pre-wrap; border: 1px solid #c8d1d1; border-radius: 8px; background: #fff; padding: 10px 12px; font-size: 15px; line-height: 1.4; }
    textarea { width: 100%; min-height: 76px; border: 1px solid #c8d1d1; border-radius: 8px; padding: 10px 12px; font: inherit; resize: vertical; }
    .empty { color: #7b8d90; }
    .health-list { display: grid; gap: 6px; }
    .row { display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; gap: 8px; align-items: center; min-height: 24px; font-size: 13px; }
    .row .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .row .meta { color: #506067; font-variant-numeric: tabular-nums; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #aeb9bd; }
    .ok { background: #1f9d55; }
    .warn { background: #d88910; }
    .bad { background: #cf3f3f; }
    .topic-table { display: grid; gap: 4px; }
    .topic-row { display: grid; grid-template-columns: minmax(0, 1fr) 54px 54px; gap: 8px; align-items: center; font-size: 13px; min-height: 24px; }
    .topic-row.header { color: #506067; font-size: 11px; font-weight: 850; text-transform: uppercase; }
    .topic-row .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .topic-row .count { text-align: right; font-variant-numeric: tabular-nums; }
    .chain-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
    .chain-card { border: 1px solid #d7e0e2; border-radius: 8px; padding: 8px; min-width: 0; background: #fbfcfc; }
    .chain-card h3 { margin: 0 0 5px; font-size: 11px; color: #506067; text-transform: uppercase; }
    .chain-card b { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
    .chain-card span { display: block; color: #506067; font-size: 11px; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    pre { white-space: pre-wrap; word-break: break-word; background: #172126; color: #e8f0ef; border-radius: 8px; padding: 14px; min-height: 250px; max-height: 360px; overflow: auto; margin: 0; font-size: 12px; }
    @media (max-width: 1100px) {
      main { padding: 12px; }
      .dashboard { grid-template-columns: 1fr; }
      .status-grid { grid-template-columns: 1fr; }
      .chain-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Week3 Robot Control</h1>
      <p class="subtitle">Server PC dashboard for ROS2 graph, ASR, TTS, AV, TB3 face state, and Week5 behavior execution</p>
    </div>
    <div id="clock" class="clock">loading...</div>
  </header>
  <section class="dashboard">
    <aside class="stack">
      <div class="panel">
        <p class="panel-title">Control</p>
        <div class="buttons">
          <button id="asr" class="control-btn accent">Start ASR 5s</button>
          <button id="tts" class="control-btn accent">Speak TTS</button>
          <button id="record" class="control-btn">Record AV 5s</button>
          <button id="refresh" class="control-btn">Refresh Status</button>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">Week5 Behavior</p>
        <textarea id="prompt" placeholder="Optional text-only prompt"></textarea>
        <div class="buttons" style="margin-top:10px">
          <button id="ai-dry-run" class="control-btn accent">Dry-run AI response</button>
          <button id="ai-run" class="control-btn accent">Run AI response</button>
          <button id="test-plan" class="control-btn">Publish test plan</button>
          <button id="stop" class="control-btn danger">Stop</button>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">Expression</p>
        <div class="expr-grid">
          <button data-expression="neutral">Neutral</button>
          <button data-expression="happy">Happy</button>
          <button data-expression="thinking">Thinking</button>
          <button data-expression="surprised">Surprise</button>
          <button data-expression="comforting">Comfort</button>
          <button data-expression="concerned">Concern</button>
          <button data-expression="sad">Sad</button>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">Services</p>
        <div id="services" class="health-list"></div>
      </div>
    </aside>
    <section class="stack">
      <div class="panel">
        <p class="panel-title">Latest Speech Pipeline</p>
        <div class="status-grid">
          <div class="card">
            <h3>ASR</h3>
            <div class="metric"><span>state</span><b id="asrState">-</b></div>
            <div class="metric"><span>latency</span><b id="asrLatency">-</b></div>
            <div class="metric"><span>language</span><b id="asrLang">-</b></div>
          </div>
          <div class="card">
            <h3>TTS</h3>
            <div class="metric"><span>state</span><b id="ttsState">-</b></div>
            <div class="metric"><span>latency</span><b id="ttsLatency">-</b></div>
            <div class="metric"><span>duration</span><b id="ttsDuration">-</b></div>
          </div>
          <div class="card">
            <h3>AV</h3>
            <div class="metric"><span>state</span><b id="avState">-</b></div>
            <div class="metric"><span>frames</span><b id="avFrames">-</b></div>
            <div class="metric"><span>audio</span><b id="avAudio">-</b></div>
          </div>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">Week5 Behavior Status</p>
        <div class="status-grid">
          <div class="card"><h3>AI</h3><div class="metric"><span>state</span><b id="aiState">-</b></div></div>
          <div class="card"><h3>Behavior</h3><div class="metric"><span>state</span><b id="behaviorState">-</b></div></div>
          <div class="card"><h3>Expression</h3><div class="metric"><span>state</span><b id="expressionState">-</b></div></div>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">AI Chain Status</p>
        <div class="chain-grid">
          <div class="chain-card"><h3>Request</h3><b id="chainRequest">-</b><span id="chainModel">-</span></div>
          <div class="chain-card"><h3>ASR/Text</h3><b id="chainAsr">-</b><span id="chainText">-</span></div>
          <div class="chain-card"><h3>Camera</h3><b id="chainCamera">-</b><span id="chainImage">-</span></div>
          <div class="chain-card"><h3>VLM</h3><b id="chainVlm">-</b><span id="chainTotal">-</span></div>
          <div class="chain-card"><h3>Validator</h3><b id="chainValidation">-</b><span id="chainFallback">-</span></div>
          <div class="chain-card"><h3>Publish</h3><b id="chainPublish">-</b><span id="chainTopic">-</span></div>
          <div class="chain-card"><h3>Executor</h3><b id="chainExecutor">-</b><span id="chainExecutorMode">-</span></div>
          <div class="chain-card"><h3>TTS</h3><b id="chainTts">-</b><span id="chainSpeechText">-</span></div>
          <div class="chain-card"><h3>Speech/Motion</h3><b id="chainSpeech">-</b><span id="chainMotion">-</span></div>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">ASR Text</p>
        <div id="asrText" class="textbar empty">ASR text will appear here</div>
      </div>
      <div class="panel">
        <p class="panel-title">TTS Text</p>
        <div id="ttsText" class="textbar empty">TTS text will appear here</div>
      </div>
      <div class="panel">
        <p class="panel-title">TB3 Face Server</p>
        <div class="status-grid">
          <div class="card"><h3>Reachability</h3><div class="metric"><span>state</span><b id="faceReach">-</b></div></div>
          <div class="card"><h3>Expression</h3><div class="metric"><span>current</span><b id="faceExpr">-</b></div></div>
          <div class="card"><h3>Updated</h3><div class="metric"><span>age</span><b id="faceAge">-</b></div></div>
        </div>
      </div>
      <div class="panel">
        <p class="panel-title">Raw Status</p>
        <pre id="status">loading...</pre>
      </div>
    </section>
    <section class="stack">
      <div class="panel">
        <p class="panel-title">ROS Nodes</p>
        <div id="nodes" class="health-list"></div>
      </div>
      <div class="panel">
        <p class="panel-title">ROS Topics</p>
        <div id="topics" class="topic-table"></div>
      </div>
    </section>
  </section>
</main>
<script>
let asrRecording = false;

async function post(path, body) {
  await fetch(path, {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body});
  await refresh();
}

function cleanAsrText(value) {
  return String(value || "").replace(/<\\|[^|]+\\|>/g, "").trim();
}

function parseMaybeJson(value) {
  if (!value || value === "none") return {};
  try { return JSON.parse(value); } catch (e) { return {raw: String(value)}; }
}

function compactStatus(payload, fallback = "-") {
  if (!payload || Object.keys(payload).length === 0) return fallback || "-";
  if (payload.raw) return payload.raw;
  const state = payload.state || payload.status || "-";
  const input = payload.trace_id || payload.input_id || payload.request_id || "";
  const suffix = payload.fallback_used ? " fallback" : "";
  return input ? state + " " + input + suffix : state + suffix;
}

function traceOf(payload) {
  return payload && (payload.trace_id || payload.input_id || payload.request_id || "");
}

function statusForTrace(payload, trace) {
  if (!trace || !payload || Object.keys(payload).length === 0 || payload.raw) return payload || {};
  const payloadTrace = traceOf(payload);
  if (!payloadTrace || payloadTrace === trace) return payload;
  return {state: "stale", trace_id: payloadTrace, expected_trace_id: trace};
}

function fmtMs(value) {
  const n = Number(value || 0);
  return n > 0 ? n + " ms" : "-";
}

function fmtSec(value) {
  const n = Number(value || 0);
  return n > 0 ? n.toFixed(2) + " s" : "-";
}

function fmtBytes(value) {
  const n = Number(value || 0);
  if (!n) return "-";
  if (n > 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB";
  return Math.round(n / 1024) + " KB";
}

function setText(id, value, emptyText = "-") {
  document.getElementById(id).textContent = value || emptyText;
}

function setChain(id, value, emptyText = "-") {
  const el = document.getElementById(id);
  if (el) el.textContent = value || emptyText;
}

function fillTextbar(id, value, placeholder) {
  const el = document.getElementById(id);
  const text = value || "";
  el.textContent = text || placeholder;
  el.classList.toggle("empty", !text);
}

function dotClass(state) {
  if (state === true || state === "ok") return "ok";
  if (state === "warn" || state === "stale" || state === "starting" || state === "unknown") return "warn";
  return "bad";
}

function renderHealth(id, items) {
  const root = document.getElementById(id);
  root.innerHTML = "";
  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<span class="dot ${dotClass(item.state || (item.ok ? "ok" : "bad"))}"></span><span class="name"></span><span class="meta"></span>`;
    row.querySelector(".name").textContent = item.name;
    row.querySelector(".meta").textContent = item.meta || (item.ok ? "ok" : "missing");
    root.appendChild(row);
  });
}

function renderTopics(topics) {
  const root = document.getElementById("topics");
  root.innerHTML = `<div class="topic-row header"><span>topic</span><span class="count">pub</span><span class="count">sub</span></div>`;
  topics.forEach(topic => {
    const ok = topic.publishers > 0 || topic.subscribers > 0;
    const row = document.createElement("div");
    row.className = "topic-row";
    row.innerHTML = `<span class="name"></span><span class="count"></span><span class="count"></span>`;
    row.querySelector(".name").textContent = (ok ? "* " : "- ") + topic.name;
    row.querySelectorAll(".count")[0].textContent = topic.publishers;
    row.querySelectorAll(".count")[1].textContent = topic.subscribers;
    root.appendChild(row);
  });
}

async function startAsr() {
  asrRecording = true;
  document.getElementById("asrText").classList.remove("empty");
  document.getElementById("asrText").textContent = "Listening...";
  await post("/api/asr", "duration=5&language=auto");
}

function promptBody(mode) {
  return "mode=" + encodeURIComponent(mode) + "&text=" + encodeURIComponent(document.getElementById("prompt").value);
}

document.querySelectorAll("[data-expression]").forEach(b => {
  b.onclick = () => post("/api/expression", "value=" + encodeURIComponent(b.dataset.expression));
});
document.getElementById("record").onclick = () => post("/api/record", "duration=5&label=server_ui");
document.getElementById("asr").onclick = startAsr;
document.getElementById("tts").onclick = () => post("/api/tts", "language=auto&text=" + encodeURIComponent(document.getElementById("prompt").value));
document.getElementById("refresh").onclick = refresh;
document.getElementById("ai-dry-run").onclick = () => post("/api/ai_response", promptBody("dry_run"));
document.getElementById("ai-run").onclick = () => post("/api/ai_response", promptBody("run"));
document.getElementById("test-plan").onclick = () => post("/api/test_plan", "source=server_control_ui");
document.getElementById("stop").onclick = () => post("/api/stop", "source=server_control_ui");

async function refresh() {
  try {
    const data = await fetch("/status.json?ts=" + Date.now()).then(r => r.json());
    const now = Date.now() / 1000;
    document.getElementById("clock").textContent = "updated " + new Date(data.time * 1000).toLocaleTimeString();
    document.getElementById("status").textContent = JSON.stringify(data, null, 2);
    const asrText = cleanAsrText(data.asr_text);
    const parsedStatus = parseMaybeJson(data.asr_status);
    const ttsStatus = parseMaybeJson(data.tts_status);
    const speechStatus = parseMaybeJson(data.speech_status);
    const avStatus = parseMaybeJson(data.av_status);
    const aiStatus = parseMaybeJson(data.ai_status);
    const behaviorStatus = parseMaybeJson(data.behavior_status);
    const face = data.face_server || {};
    const timings = aiStatus.timings || {};
    const chainTrace = traceOf(aiStatus) || traceOf(behaviorStatus) || traceOf(ttsStatus) || "";
    const chainBehavior = statusForTrace(behaviorStatus, chainTrace);
    const chainTts = statusForTrace(ttsStatus, chainTrace);
    const chainSpeechStatus = statusForTrace(speechStatus, chainTrace);

    setText("asrState", parsedStatus.state || "-");
    setText("asrLatency", fmtMs(parsedStatus.latency_ms));
    setText("asrLang", parsedStatus.language || "-");
    setText("ttsState", ttsStatus.state || "-");
    setText("ttsLatency", fmtMs(ttsStatus.latency_ms));
    setText("ttsDuration", fmtSec(ttsStatus.audio_duration_s));
    setText("avState", avStatus.state || (avStatus.ok === true ? "done" : "-"));
    setText("avFrames", avStatus.frames || "-");
    setText("avAudio", fmtBytes(avStatus.audio_bytes));
    setText("aiState", compactStatus(aiStatus, data.ai_status));
    setText("behaviorState", compactStatus(behaviorStatus, data.behavior_status));
    setText("expressionState", data.expression_status || "-");
    setText("faceReach", face.ok ? "ok" : "offline");
    setText("faceExpr", face.state && face.state.expression || "-");
    setText("faceAge", face.state && face.state.updated_at ? fmtSec(now - face.state.updated_at) : "-");
    fillTextbar("ttsText", ttsStatus.text || "", "TTS text will appear here");
    setChain("chainRequest", compactStatus(aiStatus, "-"));
    setChain("chainModel", aiStatus.model || "-");
    setChain("chainAsr", (timings.text_source || "-") + " " + (fmtMs(timings.asr_ms || timings.text_ms)));
    setChain("chainText", aiStatus.text || cleanAsrText(data.asr_text) || "-");
    setChain("chainCamera", fmtMs(timings.camera_wait_ms));
    setChain("chainImage", fmtBytes(aiStatus.image_bytes));
    setChain("chainVlm", fmtMs(aiStatus.vlm_latency_ms || timings.vlm_ms));
    setChain("chainTotal", "total " + fmtMs(timings.total_ms || aiStatus.latency_ms));
    setChain("chainValidation", (aiStatus.accepted === true ? "accepted " : aiStatus.accepted === false ? "fallback " : "") + fmtMs(aiStatus.validation_latency_ms || timings.validation_ms));
    setChain("chainFallback", aiStatus.fallback_reason || (aiStatus.errors && aiStatus.errors.join("; ")) || "-");
    setChain("chainPublish", fmtMs(timings.publish_ms));
    setChain("chainTopic", aiStatus.topic || "-");
    setChain("chainExecutor", compactStatus(chainBehavior, "-"));
    setChain("chainExecutorMode", chainBehavior.effective_dry_run ? "dry-run" : chainBehavior.state === "stale" ? "stale" : chainBehavior.state ? "hardware" : "-");
    setChain("chainTts", (chainTts.state || "-") + " " + fmtMs(chainTts.latency_ms));
    setChain("chainSpeechText", chainTts.text || (chainTts.state === "stale" ? "stale trace " + traceOf(chainTts) : "-"));
    setChain("chainSpeech", (chainSpeechStatus.state || chainSpeechStatus.raw || "-") + " / " + (chainBehavior.payload && chainBehavior.payload.action || chainBehavior.face || "-"));
    setChain("chainMotion", chainBehavior.payload ? JSON.stringify(chainBehavior.payload) : chainBehavior.state === "stale" ? "stale trace " + traceOf(chainBehavior) : "-");
    renderHealth("services", data.services || []);
    renderHealth("nodes", data.nodes || []);
    renderTopics(data.topic_monitor || []);

    if (asrText) {
      fillTextbar("asrText", asrText, "ASR text will appear here");
    } else if (parsedStatus.state && parsedStatus.state !== "done") {
      fillTextbar("asrText", parsedStatus.state, "ASR text will appear here");
    }
    if (parsedStatus.state === "done" || parsedStatus.ok === false) {
      asrRecording = false;
    }
  } catch (e) {
    document.getElementById("status").textContent = String(e);
  }
}
setInterval(refresh, 1500);
refresh();
</script>
</body>
</html>
"""


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class ServerControl(Node):
    EXPECTED_NODES = [
        'server_control_node',
        'av_recorder_node',
        'asr_topic_adapter_node',
        'tts_topic_adapter_node',
        'face_display_node',
        'mic_capture_node',
        'camera_capture_node',
        'speech_player_node',
        'motion_controller_node',
        'expression_behavior_node',
        'behavior_executor_node',
        'vlm_behavior_client_node',
    ]

    MONITORED_TOPICS = [
        '/robot_audio/pcm',
        '/robot_camera/jpeg',
        '/robot_av/record_request',
        '/robot_av/status',
        '/robot_asr/request',
        '/robot_asr/text',
        '/robot_asr/status',
        '/robot_tts/request',
        '/robot_tts/status',
        '/robot_speech/wav',
        '/robot_speech/status',
        '/robot_expression/trigger',
        '/robot_expression/status',
        '/robot_ai/response_request',
        '/robot_ai/status',
        '/robot_behavior/plan',
        '/robot_behavior/status',
        '/robot_motion/action_cmd',
        '/emergency_stop',
        '/cmd_vel',
        '/odom',
    ]

    SERVICES = [
        ('turtlebot3', ['mic_capture_node', 'camera_capture_node', 'speech_player_node']),
        ('tb3_asr', ['asr_topic_adapter_node']),
        ('tb3_tts', ['tts_topic_adapter_node']),
        ('server_ui', ['server_control_node', 'av_recorder_node']),
        ('vlm', ['vlm_behavior_client_node']),
        ('behavior', ['behavior_executor_node']),
    ]

    def __init__(self):
        super().__init__('server_control_node')
        self.declare_parameter('port', 8775)
        self.declare_parameter('face_state_url', 'http://192.168.250.10:8765/state.json')
        self.declare_parameter('node_monitor_grace_sec', 12.0)
        self.port = int(self.get_parameter('port').value)
        self.face_state_url = str(self.get_parameter('face_state_url').value)
        self.node_monitor_grace_sec = float(self.get_parameter('node_monitor_grace_sec').value)
        self.trigger_pub = self.create_publisher(String, '/robot_expression/trigger', 10)
        self.record_pub = self.create_publisher(String, '/robot_av/record_request', 10)
        self.asr_pub = self.create_publisher(String, '/robot_asr/request', 10)
        self.tts_pub = self.create_publisher(String, '/robot_tts/request', 10)
        self.ai_request_pub = self.create_publisher(String, '/robot_ai/response_request', 10)
        self.behavior_plan_pub = self.create_publisher(String, '/robot_behavior/plan', 10)
        self.motion_pub = self.create_publisher(String, '/robot_motion/action_cmd', 10)
        self.emergency_stop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.create_subscription(String, '/robot_av/status', self.on_av_status, 10)
        self.create_subscription(String, '/robot_expression/status', self.on_expression_status, 10)
        self.create_subscription(String, '/robot_behavior/status', self.on_behavior_status, 10)
        self.create_subscription(String, '/robot_asr/text', self.on_asr_text, 10)
        self.create_subscription(String, '/robot_asr/status', self.on_asr_status, 10)
        self.create_subscription(String, '/robot_tts/status', self.on_tts_status, 10)
        self.create_subscription(String, '/robot_speech/status', self.on_speech_status, 10)
        self.create_subscription(String, '/robot_ai/status', self.on_ai_status, 10)
        self._lock = threading.Lock()
        self._av_status = 'none'
        self._expression_status = 'none'
        self._behavior_status = 'none'
        self._asr_text = ''
        self._asr_status = 'none'
        self._tts_status = 'none'
        self._speech_status = 'none'
        self._ai_status = 'none'
        self._node_last_seen = {}
        self._last_node_monitor_error = ''
        self._last_node_monitor_time = 0.0
        self._last_node_count = 0
        self.server = self.start_server()
        self.get_logger().info(f'Server control UI serving http://localhost:{self.port}/')

    def start_server(self):
        handler = self.make_handler()
        server = ReusableThreadingHTTPServer(('0.0.0.0', self.port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def make_handler(self):
        node = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_GET(self):
                if self.path.startswith('/status.json'):
                    self.send_json(node.status())
                else:
                    data = HTML.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            def do_POST(self):
                size = int(self.headers.get('Content-Length', '0'))
                body = self.rfile.read(size).decode('utf-8')
                self.send_json(node.handle_api(self.path, body))

            def send_json(self, payload):
                data = json.dumps(payload).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        return Handler

    def handle_api(self, path, body):
        data = parse_qs(body)
        if path == '/api/expression':
            expression = data.get('value', ['neutral'])[0]
            self.publish_string(self.trigger_pub, expression)
            return {'ok': True, 'expression': expression}
        if path == '/api/record':
            duration = data.get('duration', ['5'])[0]
            label = data.get('label', ['server_ui'])[0]
            self.publish_string(self.record_pub, json.dumps({'duration': float(duration), 'label': label}))
            return {'ok': True, 'duration': duration, 'label': label}
        if path == '/api/asr':
            duration = max(1.0, min(float(data.get('duration', ['5'])[0]), 10.0))
            language = data.get('language', ['auto'])[0]
            with self._lock:
                self._asr_text = ''
                self._asr_status = 'requesting'
            self.publish_string(self.asr_pub, json.dumps({'duration': duration, 'language': language}))
            return {'ok': True, 'duration': duration, 'language': language}
        if path == '/api/tts':
            language = data.get('language', ['auto'])[0]
            text = data.get('text', [''])[0].strip()
            with self._lock:
                if not text:
                    text = self.clean_asr_text(self._asr_text)
                if not text:
                    self._tts_status = json.dumps(
                        {'ok': False, 'state': 'empty_text', 'language': language, 'text': '', 'time': time.time()},
                        separators=(',', ':'),
                    )
                    return {'ok': False, 'error': 'empty_text'}
                self._tts_status = json.dumps(
                    {'ok': True, 'state': 'requesting', 'language': language, 'text': text, 'time': time.time()},
                    ensure_ascii=False,
                    separators=(',', ':'),
                )
            self.publish_string(
                self.tts_pub,
                json.dumps(
                    {'text': text, 'language': language, 'source': 'server_control_ui'},
                    ensure_ascii=False,
                    separators=(',', ':'),
                ),
            )
            return {'ok': True, 'language': language, 'text': text}
        if path == '/api/ai_response':
            mode = data.get('mode', ['dry_run'])[0]
            text = data.get('text', [''])[0]
            context_session = data.get('context_session', [''])[0]
            return self.request_ai_response(mode, text, context_session)
        if path == '/api/test_plan':
            source = data.get('source', ['server_control_ui'])[0]
            return self.publish_test_plan(source)
        if path == '/api/stop':
            source = data.get('source', ['server_control_ui'])[0]
            return self.stop_robot(source)
        return {'ok': False, 'error': 'unknown endpoint'}

    def status(self):
        started = time.perf_counter()
        topic_types = self.topic_types()
        nodes = self.node_monitor()
        services = self.service_monitor(nodes)
        topic_monitor = self.topic_monitor(topic_types)
        face_server = self.face_server_state()
        stale_nodes = [item['name'] for item in nodes if item.get('state') == 'stale']
        missing_nodes = [item['name'] for item in nodes if item.get('state') == 'missing']
        topics = {}
        for name, types in self.get_topic_names_and_types():
            if name.startswith(('/robot_', '/cmd_vel', '/odom')):
                topics[name] = types
        with self._lock:
            return {
                'time': time.time(),
                'diagnostics': {
                    'refresh_latency_ms': int((time.perf_counter() - started) * 1000),
                    'node_monitor_time': self._last_node_monitor_time,
                    'node_count': self._last_node_count,
                    'stale_nodes': stale_nodes,
                    'missing_nodes': missing_nodes,
                    'node_monitor_error': self._last_node_monitor_error,
                    'node_monitor_grace_sec': self.node_monitor_grace_sec,
                    'face_state_url': self.face_state_url,
                },
                'av_status': self._av_status,
                'expression_status': self._expression_status,
                'behavior_status': self._behavior_status,
                'asr_text': self._asr_text,
                'asr_status': self._asr_status,
                'tts_status': self._tts_status,
                'speech_status': self._speech_status,
                'ai_status': self._ai_status,
                'services': services,
                'nodes': nodes,
                'topic_monitor': topic_monitor,
                'face_server': face_server,
                'topics': topics,
            }

    def topic_types(self):
        return {name: types for name, types in self.get_topic_names_and_types()}

    def node_monitor(self):
        now = time.time()
        try:
            present = {name for name, _namespace in self.get_node_names_and_namespaces()}
            self._last_node_monitor_error = ''
            self._last_node_monitor_time = now
            self._last_node_count = len(present)
            for name in present:
                self._node_last_seen[name] = now
        except Exception as exc:
            present = set()
            self._last_node_monitor_error = f'{type(exc).__name__}: {exc}'
        rows = []
        for name in self.EXPECTED_NODES:
            if name in present:
                rows.append({'name': name, 'ok': True, 'state': 'ok', 'last_seen': now, 'meta': 'ok'})
                continue
            age = now - self._node_last_seen.get(name, 0.0)
            if age <= self.node_monitor_grace_sec:
                rows.append(
                    {
                        'name': name,
                        'ok': True,
                        'state': 'stale',
                        'last_seen': self._node_last_seen.get(name, 0.0),
                        'meta': f'stale {age:.1f}s',
                    }
                )
            else:
                rows.append(
                    {
                        'name': name,
                        'ok': False,
                        'state': 'missing',
                        'last_seen': self._node_last_seen.get(name, 0.0),
                        'meta': 'missing',
                    }
                )
        return rows

    def service_monitor(self, nodes):
        node_state = {item['name']: item['ok'] for item in nodes}
        output = []
        for name, required in self.SERVICES:
            missing = [node for node in required if not node_state.get(node)]
            output.append(
                {
                    'name': name,
                    'ok': not missing,
                    'state': 'ok' if not missing else 'missing',
                    'meta': 'ok' if not missing else 'missing ' + ', '.join(missing),
                }
            )
        return output

    def topic_monitor(self, topics):
        output = []
        for name in self.MONITORED_TOPICS:
            output.append(
                {
                    'name': name,
                    'types': topics.get(name, []),
                    'publishers': self.count_publishers(name),
                    'subscribers': self.count_subscribers(name),
                }
            )
        return output

    def face_server_state(self):
        started = time.perf_counter()
        try:
            with urlrequest.urlopen(self.face_state_url, timeout=0.35) as response:
                payload = json.loads(response.read().decode('utf-8'))
            return {
                'ok': True,
                'url': self.face_state_url,
                'latency_ms': int((time.perf_counter() - started) * 1000),
                'state': payload,
            }
        except Exception as exc:
            return {
                'ok': False,
                'url': self.face_state_url,
                'latency_ms': int((time.perf_counter() - started) * 1000),
                'error': str(exc),
            }

    def on_av_status(self, msg):
        with self._lock:
            self._av_status = msg.data

    def on_expression_status(self, msg):
        with self._lock:
            self._expression_status = msg.data

    def on_behavior_status(self, msg):
        with self._lock:
            self._behavior_status = msg.data[-2000:]

    def on_asr_text(self, msg):
        with self._lock:
            self._asr_text = msg.data

    def on_asr_status(self, msg):
        with self._lock:
            self._asr_status = msg.data[-240:]

    def on_tts_status(self, msg):
        with self._lock:
            self._tts_status = msg.data[-1200:]

    def on_ai_status(self, msg):
        with self._lock:
            self._ai_status = msg.data[-3000:]

    def on_speech_status(self, msg):
        with self._lock:
            self._speech_status = msg.data[-240:]

    def publish_string(self, publisher, value):
        msg = String()
        msg.data = value
        publisher.publish(msg)

    def publish_bool(self, publisher, value):
        msg = Bool()
        msg.data = bool(value)
        publisher.publish(msg)

    def clean_asr_text(self, text):
        value = str(text or '')
        while '<|' in value and '|>' in value:
            start = value.find('<|')
            end = value.find('|>', start)
            if end < start:
                break
            value = value[:start] + value[end + 2:]
        return value.strip()

    def request_ai_response(self, mode, text, context_session=''):
        trace_id = f'server_ui_{int(time.time() * 1000)}'
        payload = {
            'request_id': trace_id,
            'trace_id': trace_id,
            'source': 'server_control_ui',
            'mode': mode,
            'text': text.strip(),
            'record': not bool(text.strip()),
            'include_asr': not bool(text.strip()),
            'include_camera': True,
            'time': time.time(),
        }
        if str(context_session or '').strip():
            payload['context_session'] = str(context_session).strip()
        self.publish_string(self.ai_request_pub, json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
        with self._lock:
            self._ai_status = f'requested {mode}'
        return {'ok': True, 'request': payload}

    def publish_test_plan(self, source):
        trace_id = f'server_ui_test_{int(time.time())}'
        plan = {
            'input_id': trace_id,
            'trace_id': trace_id,
            'source': source,
            'validated': True,
            'fallback_used': False,
            'reply': 'I received the test plan. I will stay here.',
            'emotion': 'neutral',
            'tts_style': 'calm',
            'face': 'neutral',
            'motion': [{'action': 'stop', 'duration': 0.2}],
        }
        self.publish_string(self.behavior_plan_pub, json.dumps(plan, separators=(',', ':')))
        return {'ok': True, 'plan': plan}

    def stop_robot(self, source):
        self.publish_bool(self.emergency_stop_pub, True)
        self.publish_string(self.motion_pub, 'stop')
        with self._lock:
            self._ai_status = f'stopped by {source}'
            self._behavior_status = 'stop requested'
        return {'ok': True, 'source': source}

    def compact_status(self, raw):
        try:
            payload = json.loads(raw)
        except Exception:
            return raw[-240:]
        state = payload.get('state') or payload.get('state_name') or payload.get('status') or 'unknown'
        input_id = payload.get('input_id', '')
        trace_id = payload.get('trace_id', input_id)
        fallback = payload.get('fallback_used', False)
        suffix = ' fallback' if fallback else ''
        if trace_id:
            return f'{state} {trace_id}{suffix}'
        return f'{state}{suffix}'

    def destroy_node(self):
        if hasattr(self, 'server'):
            self.server.shutdown()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ServerControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
