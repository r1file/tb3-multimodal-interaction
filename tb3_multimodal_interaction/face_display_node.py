import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import parse_qs

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TB3 Face</title>
  <style>
    :root { color-scheme: light; }
    html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: #f3f6f2; color: #172026; font-family: "Noto Sans CJK JP", "Noto Sans CJK SC", "Noto Sans CJK TC", system-ui, sans-serif; }
    main { width: 100vw; height: 100vh; display: grid; grid-template-columns: 170px minmax(0, 1fr) 160px; gap: 8px; box-sizing: border-box; padding: 8px; background: linear-gradient(135deg, #f3f6f2 0%, #dfeee8 100%); }
    .stage { display: grid; grid-template-rows: 40px minmax(0, 1fr) 40px; place-items: center; min-width: 0; min-height: 0; gap: 7px; }
    .face { width: min(100%, 326px); max-height: 372px; aspect-ratio: 1.35; border: 0; border-radius: 22px; background: #fff4cf; position: relative; box-shadow: inset 0 -12px 0 rgba(0,0,0,.07), 0 10px 24px rgba(41,61,66,.22); animation: idle-breathe 4.2s ease-in-out infinite; touch-action: manipulation; }
    .face:active { transform: translateY(1px) scale(.995); }
    .face.listening { background: #ffe2a0; }
    .face.speaking { background: #d7f1ff; }
    .eye { position: absolute; top: 34%; width: 42px; height: 42px; border-radius: 50%; background: #172026; transition: all .18s ease; animation: blink 5.6s infinite; pointer-events: none; }
    .eye.left { left: 25%; }
    .eye.right { right: 25%; }
    .mouth { position: absolute; left: 50%; top: 59%; width: 112px; height: 50px; transform: translateX(-50%); border-bottom: 11px solid #172026; border-radius: 0 0 90px 90px; transition: all .18s ease; pointer-events: none; }
    .label { position: absolute; bottom: 10px; left: 0; right: 0; text-align: center; color: #172026; font-size: 16px; font-weight: 800; pointer-events: none; }
    .sad .mouth { top: 68%; border-bottom: 0; border-top: 12px solid #172026; border-radius: 90px 90px 0 0; }
    .happy .eye { height: 18px; border-radius: 18px; top: 40%; }
    .happy .mouth { width: 136px; height: 62px; }
    .surprised .mouth { width: 58px; height: 58px; border: 10px solid #172026; border-radius: 50%; top: 58%; }
    .thinking .eye.right { height: 14px; border-radius: 14px; top: 42%; }
    .concerned .eye { width: 56px; height: 20px; border-radius: 20px; transform: rotate(8deg); top: 38%; }
    .concerned .eye.right { transform: rotate(-8deg); }
    .comforting.face { background: #fff0cf; }
    .neutral .mouth { width: 105px; height: 0; border-bottom-width: 10px; border-radius: 16px; top: 65%; }
    .panel { min-width: 0; min-height: 0; display: grid; align-content: start; gap: 6px; }
    .control-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .expression-panel { grid-template-columns: 1fr; }
    button { min-height: 34px; border: 1px solid #b9c9c4; border-radius: 8px; background: #fffdf7; color: #172026; font-size: 12px; line-height: 1.05; font-weight: 800; padding: 4px 3px; touch-action: manipulation; }
    .wide { grid-column: 1 / -1; min-height: 36px; }
    button:active { transform: translateY(1px); background: #ffd86f; }
    button:disabled { opacity: .42; transform: none; background: #edf1ef; color: #788286; }
    button:disabled:active { transform: none; background: #edf1ef; }
    .accent { background: #cbe9df; }
    .danger { background: #ffd1c9; }
    .textbar { width: 100%; height: 40px; border: 1px solid rgba(30,50,56,.18); border-radius: 8px; background: rgba(255,255,255,.78); padding: 8px 10px; font-size: 14px; font-weight: 750; overflow-x: auto; overflow-y: hidden; white-space: nowrap; color: #172026; }
    .textbar.empty { color: #68777b; font-weight: 700; }
    .tts-text { background: rgba(240,250,255,.88); }
    .tts-text.notice { background: rgba(255,238,183,.92); color: #664400; }
    .status { grid-column: 1 / -1; font-size: 10px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; min-height: 0; }
    .status span { background: rgba(255,255,255,.72); border: 1px solid rgba(30,50,56,.12); border-radius: 6px; padding: 4px 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    @keyframes blink { 0%, 92%, 100% { transform: scaleY(1); } 94%, 96% { transform: scaleY(.12); } }
    @keyframes idle-breathe { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
    @media (max-width: 760px) {
      main { grid-template-columns: 150px minmax(0, 1fr) 142px; gap: 6px; padding: 6px; }
      .face { width: min(100%, 282px); }
      button { min-height: 32px; font-size: 11px; }
      .wide { min-height: 34px; }
      .textbar { height: 38px; font-size: 13px; }
    }
  </style>
</head>
<body>
<main>
  <section class="panel control-panel">
    <button id="asr" class="wide accent">ASR 5s</button>
    <button id="tts" class="wide accent">TTS</button>
    <button id="record" class="wide accent">Record AV</button>
    <button id="ai-response" class="wide accent">AI Response</button>
    <button id="stop" class="wide danger">Stop</button>
    <button data-volume="down">Vol-</button>
    <button data-volume="up">Vol+</button>
    <button data-volume="mute">Spk off</button>
    <button data-volume="unmute">Spk on</button>
    <button data-mic="down">Mic-</button>
    <button data-mic="up">Mic+</button>
    <button data-mic="mute">Mic off</button>
    <button data-mic="unmute">Mic on</button>
    <div class="status">
      <span id="camera">cam: ...</span>
      <span id="mic">mic: ...</span>
      <span id="speaker">spk: ...</span>
      <span id="av">av: ...</span>
      <span id="ai">ai: ...</span>
      <span id="behavior">beh: ...</span>
    </div>
  </section>
  <section class="stage">
    <div id="ttsText" class="textbar tts-text empty">TTS output</div>
    <button id="face" class="face smile" title="Start ASR">
      <div class="eye left"></div>
      <div class="eye right"></div>
      <div class="mouth"></div>
      <div id="label" class="label">smile</div>
    </button>
    <div id="asrText" class="textbar asr-text empty">tap face to speak</div>
  </section>
  <section class="panel expression-panel">
    <button data-expression="neutral">Neutral</button>
    <button data-expression="happy">Happy</button>
    <button data-expression="sad">Sad</button>
    <button data-expression="thinking">Think</button>
    <button data-expression="surprised">Surprise</button>
    <button data-expression="concerned">Concern</button>
    <button data-expression="comforting">Comfort</button>
  </section>
</main>
<script>
const allowed = new Set(["neutral","smile","happy","sad","surprised","concerned","comforting","thinking"]);
const audioBusyStates = new Set(["requesting","loading_model","synthesizing","start","playing"]);
const asrBusyStates = new Set(["requesting","recording","loading_model"]);
const aiBusyStates = new Set(["received","asr_request","vlm_request"]);
let currentAsrText = "";
function cleanAsrText(value) {
  return String(value || "").replace(/<\\|[^|]+\\|>/g, "").trim();
}
function parseMaybeJson(value) {
  if (!value || value === "none" || value === "idle") return {};
  try { return JSON.parse(value); } catch (e) { return {raw: String(value)}; }
}
function fmtMs(value) {
  const n = Number(value || 0);
  return n > 0 ? n + "ms" : "-";
}
function compactPayload(payload, fallback = "-") {
  if (!payload || Object.keys(payload).length === 0) return fallback;
  if (payload.raw) return payload.raw;
  const state = payload.state || payload.status || "-";
  const id = payload.trace_id || payload.request_id || payload.input_id || "";
  const suffix = payload.fallback_used ? " fallback" : "";
  return id ? state + " " + id + suffix : state + suffix;
}
function aiPhase(state, ai, behavior) {
  if (state.asr_state === "recording") return "Listening";
  if (ai.state === "asr_request") return "Listening";
  if (ai.state === "vlm_request") return "Thinking";
  if (behavior.state === "tts_request") return "Speaking";
  if (behavior.state === "face_publish") return "Face";
  if (behavior.state === "motion_start") return "Moving";
  if (ai.state === "received") return "Started";
  return "";
}
function setTextbar(id, text, placeholder, notice = false) {
  const box = document.getElementById(id);
  box.textContent = text || placeholder;
  box.classList.toggle("empty", !text);
  box.classList.toggle("notice", notice);
}
function isAudioBusy(state) {
  return audioBusyStates.has(String(state.tts_state || "")) || audioBusyStates.has(String(state.speech_state || ""));
}
function applyBusyGuard(state, aiPayload) {
  const audioBusy = isAudioBusy(state);
  const requestBusy = audioBusy || asrBusyStates.has(String(state.asr_state || "")) || aiBusyStates.has(String(aiPayload.state || ""));
  ["asr","face","tts","record","ai-response"].forEach(id => {
    const button = document.getElementById(id);
    if (button) button.disabled = requestBusy;
  });
  document.querySelectorAll("[data-expression]").forEach(button => {
    button.disabled = audioBusy;
  });
}
async function refresh() {
  try {
    const state = await fetch("/state.json?ts=" + Date.now()).then(r => r.json());
    const aiPayload = parseMaybeJson(state.ai_status);
    const behaviorPayload = parseMaybeJson(state.behavior_status);
    const timings = aiPayload.timings || {};
    const expression = allowed.has(state.expression) ? state.expression : "neutral";
    const face = document.getElementById("face");
    face.className = "face " + (expression === "smile" ? "happy" : expression);
    if (state.asr_state === "recording" || state.asr_state === "loading_model") {
      face.classList.add("listening");
    }
    if (isAudioBusy(state)) {
      face.classList.add("speaking");
    }
    applyBusyGuard(state, aiPayload);
    document.getElementById("label").textContent = expression;
    const text = cleanAsrText(state.asr_text);
    currentAsrText = text;
    const asrBox = document.getElementById("asrText");
    if (text) {
      asrBox.classList.remove("empty");
      asrBox.textContent = text;
    } else if (state.asr_state && state.asr_state !== "none" && state.asr_state !== "done") {
      asrBox.classList.remove("empty");
      asrBox.textContent = state.asr_state;
    }
    const phase = aiPhase(state, aiPayload, behaviorPayload);
    if (state.tts_notice) {
      setTextbar("ttsText", state.tts_notice, "TTS output", true);
    } else if (state.tts_text) {
      const prefix = state.speech_state === "playing" ? "playing: " : "";
      setTextbar("ttsText", prefix + state.tts_text, "TTS output", false);
    } else if (phase) {
      const detail = aiPayload.state === "vlm_request"
        ? "AI Thinking cam " + fmtMs(timings.camera_wait_ms)
        : "AI " + phase + " " + fmtMs(timings.total_ms || aiPayload.latency_ms);
      setTextbar("ttsText", detail, "TTS output", false);
    } else if (state.tts_state && state.tts_state !== "none" && state.tts_state !== "done") {
      setTextbar("ttsText", state.tts_state, "TTS output", false);
    }
  } catch (e) {}
}
async function post(path, body) {
  const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body});
  try {
    const payload = await response.json();
    if (payload && payload.ok === false && payload.error === "busy_speaking") {
      setTextbar("ttsText", "TTS playing; wait", "TTS output", true);
    }
  } catch (e) {}
  await refresh();
  await refreshStatus();
}
async function refreshStatus() {
  try {
    const s = await fetch("/hardware.json?ts=" + Date.now()).then(r => r.json());
    document.getElementById("camera").textContent = "camera: " + s.camera;
    document.getElementById("mic").textContent = "mic: " + s.mic;
    document.getElementById("speaker").textContent = "speaker: " + s.speaker;
    document.getElementById("av").textContent = "av: " + s.av;
    document.getElementById("ai").textContent = "ai: " + s.ai;
    document.getElementById("behavior").textContent = "behavior: " + s.behavior;
  } catch (e) {}
}
document.querySelectorAll("[data-expression]").forEach(b => b.onclick = () => post("/api/expression", "value=" + encodeURIComponent(b.dataset.expression)));
document.querySelectorAll("[data-volume]").forEach(b => b.onclick = () => post("/api/volume", "action=" + encodeURIComponent(b.dataset.volume)));
document.querySelectorAll("[data-mic]").forEach(b => b.onclick = () => post("/api/mic", "action=" + encodeURIComponent(b.dataset.mic)));
document.getElementById("asr").onclick = () => post("/api/asr", "duration=5&language=auto");
document.getElementById("face").onclick = () => post("/api/asr", "duration=5&language=auto");
document.getElementById("tts").onclick = () => post("/api/tts", "language=auto");
document.getElementById("ai-response").onclick = () => {
  setTextbar("ttsText", "AI Starting", "TTS output", false);
  setTextbar("asrText", "Listening...", "tap face to speak", false);
  post("/api/ai_response", "mode=run&source=tb3_touch_ui");
};
document.getElementById("stop").onclick = () => post("/api/stop", "source=tb3_touch_ui");
document.getElementById("record").onclick = () => post("/api/record", "duration=5&label=tb3_ui");
setInterval(refresh, 250);
setInterval(refreshStatus, 2000);
refresh();
refreshStatus();
</script>
</body>
</html>
"""


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class FaceDisplay(Node):
    def __init__(self):
        super().__init__('face_display_node')
        self.declare_parameter('web_root', '/tmp/tb3_face_gui')
        self.declare_parameter('port', 8765)
        self.web_root = Path(str(self.get_parameter('web_root').value))
        self.port = int(self.get_parameter('port').value)
        self.web_root.mkdir(parents=True, exist_ok=True)
        (self.web_root / 'index.html').write_text(HTML, encoding='utf-8')
        self._status_lock = threading.Lock()
        self._av_status = 'idle'
        self._expression = 'smile'
        self._asr_text = ''
        self._asr_state = 'none'
        self._asr_status = 'none'
        self._tts_text = ''
        self._tts_state = 'none'
        self._tts_status = 'none'
        self._tts_notice = ''
        self._speech_state = 'none'
        self._speech_status = 'none'
        self._ai_status = 'idle'
        self._behavior_status = 'idle'
        self.write_state(self._expression)

        self.create_subscription(String, '/robot_face/expression', self.on_expression, 10)
        self.status_pub = self.create_publisher(String, '/robot_face/status', 10)
        self.trigger_pub = self.create_publisher(String, '/robot_expression/trigger', 10)
        self.record_pub = self.create_publisher(String, '/robot_av/record_request', 10)
        self.asr_pub = self.create_publisher(String, '/robot_asr/request', 10)
        self.tts_pub = self.create_publisher(String, '/robot_tts/request', 10)
        self.ai_request_pub = self.create_publisher(String, '/robot_ai/response_request', 10)
        self.motion_pub = self.create_publisher(String, '/robot_motion/action_cmd', 10)
        self.emergency_stop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.create_subscription(String, '/robot_av/status', self.on_av_status, 10)
        self.create_subscription(String, '/robot_asr/text', self.on_asr_text, 10)
        self.create_subscription(String, '/robot_asr/status', self.on_asr_status, 10)
        self.create_subscription(String, '/robot_tts/status', self.on_tts_status, 10)
        self.create_subscription(String, '/robot_speech/status', self.on_speech_status, 10)
        self.create_subscription(String, '/robot_ai/status', self.on_ai_status, 10)
        self.create_subscription(String, '/robot_behavior/status', self.on_behavior_status, 10)
        self.server = self.start_server()
        self.get_logger().info(f'Face GUI serving http://localhost:{self.port}/')

    def is_audio_busy_locked(self):
        busy_states = {'requesting', 'loading_model', 'synthesizing', 'start', 'playing'}
        return self._tts_state in busy_states or self._speech_state in busy_states

    def reject_audio_busy(self, action):
        with self._status_lock:
            if not self.is_audio_busy_locked():
                return None
            payload = {
                'state': 'busy_speaking',
                'blocked_action': action,
                'tts_state': self._tts_state,
                'speech_state': self._speech_state,
                'time': time.time(),
            }
            self._tts_notice = 'TTS playing; wait'
            self._ai_status = json.dumps(payload, separators=(',', ':'))
            self.write_state(self._expression)
            return {'ok': False, 'error': 'busy_speaking', **payload}

    def start_server(self):
        handler = self.make_handler()
        server = ReusableThreadingHTTPServer(('0.0.0.0', self.port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def make_handler(self):
        node = self
        root = str(self.web_root)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=root, **kwargs)

            def log_message(self, format, *args):
                return

            def do_GET(self):
                if self.path.startswith('/hardware.json'):
                    self.send_json(node.hardware_status())
                    return
                super().do_GET()

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

    def on_expression(self, msg):
        self.set_expression(msg.data.strip(), publish_status=True)

    def on_av_status(self, msg):
        with self._status_lock:
            self._av_status = msg.data[-96:]

    def on_ai_status(self, msg):
        with self._status_lock:
            self._ai_status = msg.data[-2000:]
            self.write_state(self._expression)

    def on_behavior_status(self, msg):
        with self._status_lock:
            self._behavior_status = msg.data[-2000:]
            self.write_state(self._expression)

    def handle_api(self, path, body):
        data = parse_qs(body)
        if path == '/api/expression':
            busy = self.reject_audio_busy('expression')
            if busy:
                return busy
            expression = data.get('value', ['neutral'])[0]
            self.set_expression(expression, publish_status=True)
            self.publish_string(self.trigger_pub, expression)
            return {'ok': True, 'expression': expression}
        if path == '/api/volume':
            return self.set_volume(data.get('action', [''])[0])
        if path == '/api/mic':
            return self.set_mic(data.get('action', [''])[0])
        if path == '/api/record':
            busy = self.reject_audio_busy('record')
            if busy:
                return busy
            duration = float(data.get('duration', ['5'])[0])
            label = data.get('label', ['tb3_ui'])[0]
            self.publish_string(
                self.record_pub,
                json.dumps({'duration': duration, 'label': label}, separators=(',', ':')),
            )
            return {'ok': True, 'duration': duration, 'label': label}
        if path == '/api/asr':
            busy = self.reject_audio_busy('asr')
            if busy:
                return busy
            duration = max(1.0, min(float(data.get('duration', ['5'])[0]), 10.0))
            language = data.get('language', ['auto'])[0]
            with self._status_lock:
                self._asr_text = ''
                self._asr_state = 'requesting'
                self._asr_status = 'requesting'
                self.write_state(self._expression)
            self.publish_string(
                self.asr_pub,
                json.dumps({'duration': duration, 'language': language}, separators=(',', ':')),
            )
            return {'ok': True, 'duration': duration, 'language': language}
        if path == '/api/tts':
            busy = self.reject_audio_busy('tts')
            if busy:
                return busy
            language = data.get('language', ['auto'])[0]
            with self._status_lock:
                text = self.clean_asr_text(self._asr_text)
                if not text:
                    self._tts_notice = 'ASR text is empty'
                    self._tts_state = 'empty_text'
                    self.write_state(self._expression)
                    return {'ok': False, 'error': 'empty_asr_text'}
                self._tts_text = text
                self._tts_state = 'requesting'
                self._tts_notice = ''
                self.write_state(self._expression)
            self.publish_string(
                self.tts_pub,
                json.dumps(
                    {'text': text, 'language': language, 'source': 'tb3_ui_asr_text'},
                    ensure_ascii=False,
                    separators=(',', ':'),
                ),
            )
            return {'ok': True, 'language': language, 'text': text}
        if path == '/api/ai_response':
            mode = data.get('mode', ['run'])[0]
            source = data.get('source', ['tb3_touch_ui'])[0]
            return self.request_ai_response(mode, source)
        if path == '/api/stop':
            source = data.get('source', ['tb3_touch_ui'])[0]
            return self.stop_robot(source)
        return {'ok': False, 'error': 'unknown endpoint'}

    def set_expression(self, expression, publish_status=False):
        allowed = {'neutral', 'smile', 'happy', 'sad', 'surprised', 'concerned', 'comforting', 'thinking'}
        if expression not in allowed:
            self.get_logger().warn(f'Unknown expression {expression!r}; using neutral')
            expression = 'neutral'
        self._expression = expression
        self.write_state(expression)
        if publish_status:
            status = String()
            status.data = f'{expression} {int(time.time())}'
            self.status_pub.publish(status)
        self.get_logger().info(f'Expression set to {expression}')

    def write_state(self, expression):
        payload = {
            'expression': expression,
            'asr_text': getattr(self, '_asr_text', ''),
            'asr_state': getattr(self, '_asr_state', 'none'),
            'asr_status': getattr(self, '_asr_status', 'none'),
            'tts_text': getattr(self, '_tts_text', ''),
            'tts_state': getattr(self, '_tts_state', 'none'),
            'tts_status': getattr(self, '_tts_status', 'none'),
            'tts_notice': getattr(self, '_tts_notice', ''),
            'speech_state': getattr(self, '_speech_state', 'none'),
            'speech_status': getattr(self, '_speech_status', 'none'),
            'ai_status': getattr(self, '_ai_status', 'idle'),
            'behavior_status': getattr(self, '_behavior_status', 'idle'),
            'updated_at': time.time(),
        }
        tmp = self.web_root / 'state.json.tmp'
        tmp.write_text(json.dumps(payload), encoding='utf-8')
        os.replace(tmp, self.web_root / 'state.json')

    def hardware_status(self):
        with self._status_lock:
            av_status = self._av_status
            ai_status = self._ai_status
            behavior_status = self._behavior_status
        return {
            'camera': 'ok' if Path('/dev/video0').exists() else 'missing',
            'mic': self.describe_capture_card(('Device', 'USB PnP Sound Device', 'Camera')),
            'speaker': self.describe_playback_card('UACDemoV10'),
            'brightness': self.describe_brightness(),
            'av': av_status,
            'ai': self.compact_status(ai_status),
            'behavior': self.compact_status(behavior_status),
        }

    def publish_string(self, publisher, value):
        msg = String()
        msg.data = value
        publisher.publish(msg)

    def publish_bool(self, publisher, value):
        msg = Bool()
        msg.data = bool(value)
        publisher.publish(msg)

    def on_asr_text(self, msg):
        with self._status_lock:
            self._asr_text = msg.data
            self.write_state(self._expression)

    def on_asr_status(self, msg):
        state = 'status'
        try:
            payload = json.loads(msg.data)
            state = str(payload.get('state', state))
            if payload.get('text'):
                self._asr_text = str(payload.get('text'))
        except Exception:
            pass
        with self._status_lock:
            self._asr_status = msg.data[-180:]
            self._asr_state = state
            self.write_state(self._expression)

    def on_tts_status(self, msg):
        state = 'status'
        text = ''
        notice = ''
        try:
            payload = json.loads(msg.data)
            state = str(payload.get('state', state))
            text = str(payload.get('text') or '')
            if not payload.get('ok', True):
                notice = str(payload.get('error') or state)
        except Exception:
            pass
        with self._status_lock:
            self._tts_status = msg.data[-240:]
            self._tts_state = state
            if text:
                self._tts_text = text
            self._tts_notice = notice
            self.write_state(self._expression)

    def on_speech_status(self, msg):
        state = 'status'
        try:
            payload = json.loads(msg.data)
            state = str(payload.get('state', state))
        except Exception:
            raw = msg.data.strip()
            if raw:
                state = raw.split()[0]
        with self._status_lock:
            self._speech_status = msg.data[-180:]
            self._speech_state = state
            if state in {'done', 'idle', 'none'}:
                if self._tts_notice == 'TTS playing; wait':
                    self._tts_notice = ''
                try:
                    ai_payload = json.loads(self._ai_status)
                    if ai_payload.get('state') == 'busy_speaking':
                        self._ai_status = 'idle'
                except Exception:
                    pass
            self.write_state(self._expression)

    def clean_asr_text(self, text):
        value = str(text or '')
        while '<|' in value and '|>' in value:
            start = value.find('<|')
            end = value.find('|>', start)
            if end < start:
                break
            value = value[:start] + value[end + 2:]
        return value.strip()

    def request_ai_response(self, mode, source):
        busy = self.reject_audio_busy('ai_response')
        if busy:
            return busy
        trace_id = f'tb3_ui_{int(time.time() * 1000)}'
        payload = {
            'request_id': trace_id,
            'trace_id': trace_id,
            'source': source,
            'mode': mode,
            'record': True,
            'include_asr': True,
            'include_camera': True,
            'time': time.time(),
        }
        self.publish_string(self.ai_request_pub, json.dumps(payload, separators=(',', ':')))
        with self._status_lock:
            self._asr_text = ''
            self._asr_state = 'requesting'
            self._asr_status = 'requesting'
            self._tts_text = ''
            self._tts_state = 'none'
            self._tts_notice = ''
            self._ai_status = json.dumps(
                {
                    'state': 'requested',
                    'request_id': payload['request_id'],
                    'trace_id': payload['trace_id'],
                    'mode': mode,
                    'time': time.time(),
                },
                separators=(',', ':'),
            )
            self.write_state(self._expression)
        return {'ok': True, 'request': payload}

    def stop_robot(self, source):
        self.publish_bool(self.emergency_stop_pub, True)
        self.publish_string(self.motion_pub, 'stop')
        with self._status_lock:
            self._ai_status = f'stopped by {source}'
            self._behavior_status = 'stop requested'
        return {'ok': True, 'source': source}

    def compact_status(self, raw):
        try:
            payload = json.loads(raw)
        except Exception:
            return raw[-96:]
        state = payload.get('state', 'unknown')
        input_id = payload.get('input_id', '')
        trace_id = payload.get('trace_id', input_id)
        fallback = payload.get('fallback_used', False)
        suffix = ' fallback' if fallback else ''
        if trace_id:
            return f'{state} {trace_id}{suffix}'
        return f'{state}{suffix}'

    def describe_playback_card(self, card_names):
        return self.card_visible(['aplay', '-l'], card_names)

    def describe_capture_card(self, card_names):
        return self.card_visible(['arecord', '-l'], card_names)

    def card_visible(self, cmd, card_names):
        if isinstance(card_names, str):
            card_names = (card_names,)
        try:
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=2)
        except Exception:
            output = ''
        output += self.read_text(Path('/proc/asound/cards'))
        return 'visible' if any(name in output for name in card_names) else 'missing'

    def read_text(self, path):
        try:
            return path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return ''

    def describe_brightness(self):
        backlight = Path('/sys/class/backlight')
        if backlight.exists() and any(backlight.iterdir()):
            return 'sysfs'
        return 'unavailable'

    def set_volume(self, action):
        commands = {
            'up': ['amixer', '-c', 'UACDemoV10', 'sset', 'PCM', '5%+'],
            'down': ['amixer', '-c', 'UACDemoV10', 'sset', 'PCM', '5%-'],
            'mute': ['amixer', '-c', 'UACDemoV10', 'sset', 'PCM', 'mute'],
            'unmute': ['amixer', '-c', 'UACDemoV10', 'sset', 'PCM', 'unmute'],
        }
        cmd = commands.get(action)
        if not cmd:
            return {'ok': False, 'error': 'unknown volume action'}
        try:
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=3, check=False)
            return {'ok': result.returncode == 0, 'action': action, 'stderr': result.stderr[-120:]}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def set_mic(self, action):
        commands = {
            'up': ['amixer', '-c', 'Device', 'sset', 'Mic', '10%+'],
            'down': ['amixer', '-c', 'Device', 'sset', 'Mic', '10%-'],
            'mute': ['amixer', '-c', 'Device', 'sset', 'Mic', 'nocap'],
            'unmute': ['amixer', '-c', 'Device', 'sset', 'Mic', 'cap'],
        }
        cmd = commands.get(action)
        if not cmd:
            return {'ok': False, 'error': 'unknown mic action'}
        try:
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=3, check=False)
            return {'ok': result.returncode == 0, 'action': action, 'stderr': result.stderr[-120:]}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def destroy_node(self):
        if hasattr(self, 'server'):
            self.server.shutdown()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceDisplay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
