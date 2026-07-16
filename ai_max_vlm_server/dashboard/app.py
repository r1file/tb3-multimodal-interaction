#!/usr/bin/env python3
import html
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
PORT = int(os.environ.get("DASHBOARD_PORT", "18181"))
LLAMA_BASE_URL = os.environ.get("LLAMA_BASE_URL", "http://host.docker.internal:18082").rstrip("/")
SERVER_STATUS_URL = os.environ.get(
    "SERVER_STATUS_URL",
    "http://192.168.250.30:8775/status.json",
)
LOG_DIR = Path(os.environ.get("LLAMA_LOG_DIR", "/logs"))
TAIL_LINES = int(os.environ.get("TAIL_LINES", "80"))
LAST_RELAY_STATUS = {"time": 0.0, "data": None}
STARTED_AT = time.time()
STARTUP_GRACE_S = float(os.environ.get("STARTUP_GRACE_S", "180"))
STALE_AFTER_S = float(os.environ.get("STALE_AFTER_S", "30"))


def fetch_json(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                "ok": True,
                "status": response.status,
                "data": json.loads(response.read().decode("utf-8", errors="replace")),
                "error": "",
            }
    except Exception as exc:
        return {"ok": False, "status": 0, "data": None, "error": f"{type(exc).__name__}: {exc}"}


def fetch_text(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                "ok": True,
                "status": response.status,
                "text": response.read().decode("utf-8", errors="replace"),
                "error": "",
            }
    except Exception as exc:
        return {"ok": False, "status": 0, "text": "", "error": f"{type(exc).__name__}: {exc}"}


def parse_maybe_json(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text.startswith("{"):
        return {"raw": text}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def latest_log_file():
    if not LOG_DIR.exists():
        return None
    candidates = [path for path in LOG_DIR.glob("*.log") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def tail_file(path, lines=80):
    if not path:
        return ""
    try:
        output = subprocess.check_output(["tail", "-n", str(lines), str(path)], text=True)
        return output
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def list_llama_processes():
    try:
        output = subprocess.check_output(["ps", "-eo", "pid,etime,args"], text=True)
    except Exception as exc:
        return [{"error": f"{type(exc).__name__}: {exc}"}]
    rows = []
    for line in output.splitlines()[1:]:
        if "llama-server" not in line:
            continue
        parts = line.strip().split(None, 2)
        if len(parts) == 3:
            rows.append({"pid": parts[0], "etime": parts[1], "args": parts[2]})
    return rows


def fetch_state(fetch, payload=None):
    if fetch.get("ok"):
        timestamp = payload.get("time") if isinstance(payload, dict) else None
        if isinstance(timestamp, (int, float)) and time.time() - timestamp > STALE_AFTER_S:
            return "stale"
        return "ready"
    error = fetch.get("error", "").lower()
    if time.time() - STARTED_AT <= STARTUP_GRACE_S:
        return "starting"
    if "http error" in error:
        return "unhealthy"
    return "unreachable"


def collect_status():
    health = fetch_json(f"{LLAMA_BASE_URL}/health")
    models = fetch_json(f"{LLAMA_BASE_URL}/v1/models")
    server_status = fetch_json(SERVER_STATUS_URL)
    server_source = "direct"
    server_data = server_status.get("data") or {}
    if not server_status["ok"] and LAST_RELAY_STATUS.get("data"):
        server_source = "relay"
        server_data = LAST_RELAY_STATUS.get("data") or {}
        server_status = {
            "ok": True,
            "status": 200,
            "data": server_data,
            "error": f"using relay updated {int(time.time() - LAST_RELAY_STATUS['time'])}s ago",
        }
    relay_age_s = int(time.time() - LAST_RELAY_STATUS["time"]) if LAST_RELAY_STATUS.get("data") else None
    server_state = fetch_state(server_status, server_data)
    if server_source == "relay" and relay_age_s is not None and relay_age_s > STALE_AFTER_S:
        server_state = "stale"
    llama_state = fetch_state(health, health.get("data"))
    if health.get("ok") and not models.get("ok"):
        llama_state = "unhealthy"
    ai_status = parse_maybe_json(server_data.get("ai_status", ""))
    behavior_status = parse_maybe_json(server_data.get("behavior_status", ""))
    tts_status = parse_maybe_json(server_data.get("tts_status", ""))
    asr_status = parse_maybe_json(server_data.get("asr_status", ""))
    input_inspector = parse_maybe_json(server_data.get("input_inspector", ""))
    evaluation_status = parse_maybe_json(server_data.get("evaluation_status", ""))
    latest_log = latest_log_file()
    return {
        "time": time.time(),
        "diagnostics": {
            "state_vocabulary": {
                "starting": "inside startup grace period",
                "stale": "last usable status is older than the freshness limit",
                "missing": "an expected process, node, or container is absent",
                "unhealthy": "component responds but fails its health contract",
                "unreachable": "network endpoint cannot be contacted",
            },
            "startup_grace_s": STARTUP_GRACE_S,
            "stale_after_s": STALE_AFTER_S,
        },
        "config": {
            "llama_base_url": LLAMA_BASE_URL,
            "server_status_url": SERVER_STATUS_URL,
            "log_dir": str(LOG_DIR),
            "port": PORT,
        },
        "llama": {
            "state": llama_state,
            "health": health,
            "models": models,
            "processes": list_llama_processes(),
            "latest_log": str(latest_log) if latest_log else "",
            "latest_log_tail": tail_file(latest_log, TAIL_LINES),
        },
        "server_pc": {
            "fetch": {
                "ok": server_status["ok"],
                "status": server_status["status"],
                "error": server_status["error"],
                "source": server_source,
                "relay_age_s": relay_age_s,
                "state": server_state,
            },
            "diagnostics": server_data.get("diagnostics", {}),
            "services": server_data.get("services", []),
            "asr_text": server_data.get("asr_text", ""),
            "asr_status": asr_status,
            "ai_status": ai_status,
            "behavior_status": behavior_status,
            "tts_status": tts_status,
            "speech_status": server_data.get("speech_status", ""),
            "input_inspector": input_inspector,
            "evaluation_status": evaluation_status,
        },
    }


INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Max VLM Dashboard</title>
  <style>
    :root { color-scheme: light; --line:#d8dee4; --muted:#59636e; --ok:#116329; --bad:#b42318; --bg:#f6f8fa; --panel:#fff; }
    body { margin:0; font:14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:#1f2328; }
    header { padding:14px 18px; border-bottom:1px solid var(--line); background:#fff; display:flex; gap:14px; align-items:baseline; justify-content:space-between; }
    h1 { font-size:18px; margin:0; letter-spacing:0; }
    main { padding:16px; display:grid; gap:12px; }
    .grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:10px; }
    .wide { grid-column: span 2; }
    .full { grid-column: 1 / -1; }
    section { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; min-width:0; }
    h2 { font-size:12px; text-transform:uppercase; color:var(--muted); margin:0 0 8px; letter-spacing:.04em; }
    .value { font-size:18px; font-weight:650; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .sub { color:var(--muted); font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .ok { color:var(--ok); }
    .bad { color:var(--bad); }
    pre { margin:0; white-space:pre-wrap; word-break:break-word; max-height:360px; overflow:auto; background:#f6f8fa; border-radius:6px; padding:10px; font-size:12px; }
    table { width:100%; border-collapse:collapse; font-size:12px; }
    td, th { border-top:1px solid var(--line); padding:6px; text-align:left; vertical-align:top; }
    @media (max-width: 1000px) { .grid { grid-template-columns: repeat(2, minmax(0,1fr)); } .wide { grid-column: span 2; } }
    @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } .wide { grid-column: auto; } header { display:block; } }
  </style>
</head>
<body>
  <header>
    <h1>AI Max VLM Dashboard</h1>
    <div class="sub" id="config">loading</div>
  </header>
  <main>
    <div class="grid">
      <section><h2>Llama Health</h2><div class="value" id="health">-</div><div class="sub" id="models">-</div></section>
      <section><h2>Trace</h2><div class="value" id="trace">-</div><div class="sub" id="model">-</div></section>
      <section><h2>Validator</h2><div class="value" id="validator">-</div><div class="sub" id="fallback">-</div></section>
      <section><h2>Executor</h2><div class="value" id="executor">-</div><div class="sub" id="mode">-</div></section>
      <section class="wide"><h2>Current Input</h2><div class="value" id="input">-</div><div class="sub" id="asr">-</div></section>
      <section class="wide"><h2>Current Output</h2><div class="value" id="output">-</div><div class="sub" id="tts">-</div></section>
      <section><h2>Timing</h2><div class="value" id="timing">-</div><div class="sub" id="timing2">-</div></section>
      <section><h2>Context</h2><div class="value" id="context">-</div><div class="sub" id="context2">-</div></section>
      <section><h2>Motion</h2><div class="value" id="motion">-</div><div class="sub" id="motion2">-</div></section>
      <section><h2>Server PC</h2><div class="value" id="server">-</div><div class="sub" id="services">-</div></section>
      <section class="full"><h2>Llama Processes</h2><table id="processes"></table></section>
      <section class="full"><h2>Latest Llama Log</h2><div class="sub" id="logpath">-</div><pre id="logtail"></pre></section>
      <section class="full"><h2>Raw Status</h2><pre id="raw"></pre></section>
    </div>
  </main>
<script>
function $(id){ return document.getElementById(id); }
function asJson(v){ if (!v) return ""; try { return JSON.stringify(v); } catch { return String(v); } }
function text(v){ return v === undefined || v === null || v === "" ? "-" : String(v); }
function ms(v){ return Number.isFinite(Number(v)) ? Number(v) + " ms" : "-"; }
function modelNames(models){
  const data = models && models.data && models.data.data;
  if (Array.isArray(data)) return data.map(x => x.id || x.object || "?").join(", ");
  return models && models.error || "-";
}
async function refresh(){
  const data = await fetch("/api/status?ts=" + Date.now()).then(r => r.json());
  const ai = data.server_pc.ai_status || {};
  const behavior = data.server_pc.behavior_status || {};
  const tts = data.server_pc.tts_status || {};
  const asr = data.server_pc.asr_status || {};
  const timings = ai.timings || {};
  $("config").textContent = data.config.llama_base_url + " / " + data.config.server_status_url;
  $("health").textContent = data.llama.state;
  $("health").className = "value " + (data.llama.state === "ready" ? "ok" : "bad");
  $("models").textContent = modelNames(data.llama.models);
  $("trace").textContent = text(ai.trace_id || behavior.trace_id);
  $("model").textContent = text(ai.model);
  $("validator").textContent = ai.accepted === true ? "accepted" : ai.accepted === false ? "fallback" : text(ai.state);
  $("fallback").textContent = text(ai.policy_override || ai.fallback_reason || (ai.errors || []).join("; "));
  $("executor").textContent = text(behavior.state);
  $("mode").textContent = behavior.effective_dry_run ? "dry-run" : behavior.state ? "hardware" : "-";
  $("input").textContent = text(ai.text || data.server_pc.asr_text);
  $("asr").textContent = text(timings.text_source || asr.state) + " / " + ms(timings.asr_ms || timings.text_ms || asr.latency_ms);
  $("output").textContent = text(tts.text || ai.reply || ai.raw);
  $("tts").textContent = text(tts.language || ai.reply_language) + " / " + text(tts.state) + " / " + ms(tts.latency_ms);
  $("timing").textContent = "total " + ms(timings.total_ms || ai.latency_ms);
  $("timing2").textContent = "vlm " + ms(ai.vlm_latency_ms || timings.vlm_ms) + " / validation " + ms(ai.validation_latency_ms || timings.validation_ms);
  $("context").textContent = text(ai.context_used_reason);
  $("context2").textContent = "turns " + text(ai.context_turns) + " / candidates " + text(ai.context_candidates);
  $("motion").textContent = behavior.payload ? text(behavior.payload.action) : "-";
  $("motion2").textContent = behavior.payload ? asJson(behavior.payload) : text(behavior.face);
  $("server").textContent = data.server_pc.fetch.state;
  $("server").className = "value " + (data.server_pc.fetch.state === "ready" ? "ok" : "bad");
  $("services").textContent = text(data.server_pc.fetch.source) + " / " + (data.server_pc.services || []).map(s => s.name + ":" + s.state).join("  ");
  $("processes").innerHTML = "<tr><th>PID</th><th>Uptime</th><th>Args</th></tr>" + (data.llama.processes || []).map(p => "<tr><td>"+text(p.pid)+"</td><td>"+text(p.etime)+"</td><td>"+text(p.args || p.error)+"</td></tr>").join("");
  $("logpath").textContent = text(data.llama.latest_log);
  $("logtail").textContent = text(data.llama.latest_log_tail);
  $("raw").textContent = JSON.stringify(data, null, 2);
}
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""

# Keep the UI in a standalone asset so dashboard layout can evolve without
# mixing presentation code into status collection logic.
INDEX = (Path(__file__).with_name("index.html")).read_text(encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(collect_status())
            return
        if parsed.path in {"/", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(INDEX.encode("utf-8"))
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/server_status":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(min(length, 2_000_000))
            payload = json.loads(body.decode("utf-8", errors="replace"))
            if not isinstance(payload, dict):
                raise ValueError("payload root must be object")
        except Exception as exc:
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}).encode()
            )
            return
        LAST_RELAY_STATUS["time"] = time.time()
        LAST_RELAY_STATUS["data"] = payload
        self.send_json({"ok": True, "time": LAST_RELAY_STATUS["time"]})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def send_json(self, payload):
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AI Max VLM dashboard listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
