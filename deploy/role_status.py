#!/usr/bin/env python3
"""Emit one role-local lifecycle/health report with stable P2 state names."""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROLE = sys.argv[1] if len(sys.argv) > 1 else ""
GRACE = float(os.environ.get("ROLE_STARTUP_GRACE_S", "180"))
STALE_S = float(os.environ.get("ROLE_STATUS_STALE_S", "30"))
DASHBOARD_TIMEOUT_S = float(os.environ.get("ROLE_DASHBOARD_TIMEOUT_S", "5"))
VALID_STATES = {"starting", "stale", "missing", "unhealthy", "unreachable", "ready", "stopped"}


def run(command):
    try:
        return subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(command, 127, "", f"{type(exc).__name__}: {exc}")


def state_record(log_dir):
    path = Path(log_dir) / f"{ROLE}.state"
    try:
        state, timestamp, message = path.read_text().strip().split("|", 2)
        return {"state": state, "time": int(timestamp), "age_s": int(time.time() - int(timestamp)), "message": message, "path": str(path)}
    except (OSError, ValueError):
        return {"state": "missing", "time": 0, "age_s": None, "message": "no lifecycle state", "path": str(path)}


def http_json(url, timeout=1.5):
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body else {}
            age = None
            if isinstance(payload, dict) and isinstance(payload.get("time"), (int, float)):
                age = max(0, int(time.time() - payload["time"]))
            state = "stale" if age is not None and age > STALE_S else "ready"
            return {"state": state, "ok": state == "ready", "url": url, "status": response.status, "latency_ms": int((time.perf_counter() - started) * 1000), "age_s": age, "error": ""}, payload
    except urllib.error.HTTPError as exc:
        return {"state": "unhealthy", "ok": False, "url": url, "status": exc.code, "latency_ms": int((time.perf_counter() - started) * 1000), "age_s": None, "error": str(exc)}, {}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"state": "unreachable", "ok": False, "url": url, "status": 0, "latency_ms": int((time.perf_counter() - started) * 1000), "age_s": None, "error": f"{type(exc).__name__}: {exc}"}, {}
    except (json.JSONDecodeError, UnicodeError) as exc:
        return {"state": "unhealthy", "ok": False, "url": url, "status": 200, "latency_ms": int((time.perf_counter() - started) * 1000), "age_s": None, "error": f"invalid JSON: {exc}"}, {}


def docker_state(name):
    result = run(["docker", "inspect", "-f", "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}", name])
    if result.returncode != 0:
        return {"state": "missing", "ok": False, "name": name, "detail": "container absent"}
    status, _, health = result.stdout.strip().partition("|")
    if status != "running":
        state = "missing" if status in ("exited", "dead", "created") else "unhealthy"
    elif health and health != "healthy":
        state = "unhealthy"
    else:
        state = "ready"
    return {"state": state, "ok": state == "ready", "name": name, "detail": f"{status}{('/' + health) if health else ''}"}


def process_count(pattern, container=None):
    command = ["ps", "-eo", "args="]
    if container:
        command = ["docker", "exec", container, *command]
    result = run(command)
    if result.returncode != 0:
        return 0
    return sum(1 for line in result.stdout.splitlines() if pattern in line and "stop_matching_processes.py" not in line)


def process_component(name, pattern, container=None, expected=1):
    count = process_count(pattern, container)
    state = "ready" if count == expected else "missing" if count == 0 else "unhealthy"
    return {"state": state, "ok": state == "ready", "name": name, "count": count, "expected": expected, "pattern": pattern}


def ros_node_components(expected_nodes, container):
    setup = (
        "set +u; source /opt/ros/jazzy/setup.bash; "
        "source /workspace/ros2_ws/install/setup.bash; "
        "source /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/ros_env.sh; "
        "set -u; "
    )
    result = run(["docker", "exec", container, "bash", "-lc", setup + "timeout 10s ros2 node list"])
    nodes = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or any(node_name not in nodes for _, node_name in expected_nodes):
        fresh = run(
            [
                "docker",
                "exec",
                container,
                "bash",
                "-lc",
                setup + "timeout 20s ros2 node list --no-daemon --spin-time 5",
            ]
        )
        if fresh.returncode == 0 or result.returncode != 0:
            result = fresh
            nodes = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0:
        error = result.stderr.strip() or f"ros2 node list exited {result.returncode}"
        return [
            {"state": "unhealthy", "ok": False, "name": name, "count": None, "expected": 1, "node": node_name, "error": error}
            for name, node_name in expected_nodes
        ]
    components = []
    for name, node_name in expected_nodes:
        count = nodes.count(node_name)
        state = "ready" if count == 1 else "missing" if count == 0 else "unhealthy"
        components.append({"state": state, "ok": state == "ready", "name": name, "count": count, "expected": 1, "node": node_name})
    return components


def normalize_starting(component, lifecycle):
    if component["state"] in ("missing", "unreachable") and lifecycle["state"] == "starting" and lifecycle["age_s"] is not None and lifecycle["age_s"] <= GRACE:
        component["state"] = "starting"
    component["ok"] = component["state"] == "ready"
    return component


def dashboard_server_component(payload, lifecycle):
    fetch = payload.get("server_pc", {}).get("fetch", {}) if isinstance(payload, dict) else {}
    state = fetch.get("state")
    if state not in VALID_STATES:
        state = "unreachable"
    component = {
        "name": "server_pc",
        "state": state,
        "ok": state == "ready",
        "source": fetch.get("source", "dashboard"),
        "status": fetch.get("status", 0),
        "relay_age_s": fetch.get("relay_age_s"),
        "error": fetch.get("error", "dashboard did not report Server PC status"),
    }
    return normalize_starting(component, lifecycle)


def overall(components, lifecycle):
    states = [item["state"] for item in components]
    if lifecycle["state"] == "stopped" and not any(state in ("ready", "unhealthy") for state in states):
        return "stopped"
    for state in ("unhealthy", "missing", "unreachable", "stale", "starting"):
        if state in states:
            return state
    return "ready"


def ai_report():
    log_dir = os.environ["AI_MAX_RUNTIME_LOG_DIR"]
    lifecycle = state_record(log_dir)
    llama_http, _ = http_json(f"http://127.0.0.1:{os.environ['VLM_PORT']}/health")
    llama_proc = process_component("llama_server", "llama-server")
    dashboard = docker_state("tb3-ai-max-dashboard")
    dashboard_http, dashboard_payload = http_json(
        f"http://127.0.0.1:{os.environ['VLM_DASHBOARD_PORT']}/api/status",
        timeout=DASHBOARD_TIMEOUT_S,
    )
    server_component = dashboard_server_component(dashboard_payload, lifecycle)
    components = [
        normalize_starting({"name": "llama_http", **llama_http}, lifecycle),
        normalize_starting(llama_proc, lifecycle),
        normalize_starting(dashboard, lifecycle),
        normalize_starting({"name": "dashboard_http", **dashboard_http}, lifecycle),
        server_component,
    ]
    return lifecycle, components, {"llama": f"{os.environ['AI_MAX_ROOT']}/vlm_server_logs", "lifecycle": log_dir}


def server_report():
    log_dir = os.environ["SERVER_RUNTIME_LOG_DIR"]
    lifecycle = state_record(log_dir)
    dashboard_http, payload = http_json(f"http://127.0.0.1:{os.environ['SERVER_DASHBOARD_PORT']}/status.json")
    ai_http, _ = http_json(f"http://{os.environ['AI_MAX_IP']}:{os.environ['VLM_PORT']}/health")
    components = [docker_state(os.environ["ROS_CONTAINER"]), docker_state("tb3_asr"), docker_state("tb3_tts")]
    ros_components = ros_node_components(
        [
            ("server_control", "/server_control_node"),
            ("vlm_client", "/vlm_behavior_client_node"),
            ("evaluation_logger", "/evaluation_logger_node"),
        ],
        os.environ["ROS_CONTAINER"],
    )
    components += [
        normalize_starting({"name": "dashboard_http", **dashboard_http}, lifecycle),
        *(normalize_starting(component, lifecycle) for component in ros_components),
        normalize_starting(process_component("status_relay", "server_status_relay.py"), lifecycle),
        {"name": "ai_max", **ai_http},
    ]
    diagnostics = payload.get("diagnostics", {}) if isinstance(payload, dict) else {}
    if diagnostics.get("node_monitor_error"):
        components.append({"name": "ros_graph", "state": "unhealthy", "ok": False, "detail": diagnostics["node_monitor_error"]})
    return lifecycle, components, {"server_stack": f"{log_dir}/server_stack.log", "vlm_client": f"{log_dir}/vlm_client.log", "status_relay": f"{log_dir}/server_status_relay.log"}


def tb3_report():
    log_dir = os.environ["TB3_RUNTIME_LOG_DIR"]
    lifecycle = state_record(log_dir)
    ui_http, _ = http_json(f"http://127.0.0.1:{os.environ['TB3_UI_PORT']}/state.json")
    server_http, _ = http_json(f"http://{os.environ['SERVER_PC_IP']}:{os.environ['SERVER_DASHBOARD_PORT']}/status.json")
    components = [docker_state(os.environ["ROS_CONTAINER"])]
    ros_components = ros_node_components(
        [
            ("tb3_bringup", "/turtlebot3_node"),
            ("device_stack", "/face_display_node"),
            ("behavior_executor", "/behavior_executor_node"),
        ],
        os.environ["ROS_CONTAINER"],
    )
    components += [
        normalize_starting({"name": "face_ui", **ui_http}, lifecycle),
        *(normalize_starting(component, lifecycle) for component in ros_components),
        {"name": "server_pc", **server_http},
    ]
    return lifecycle, components, {"bringup": f"{log_dir}/tb3_bringup.log", "device_stack": f"{log_dir}/device_stack.log", "behavior_executor": f"{log_dir}/behavior_executor.log"}


def main():
    builders = {"ai_max": ai_report, "server_pc": server_report, "tb3": tb3_report}
    if ROLE not in builders:
        print("usage: role_status.py ai_max|server_pc|tb3", file=sys.stderr)
        return 2
    lifecycle, components, logs = builders[ROLE]()
    report = {"role": ROLE, "time": int(time.time()), "overall_state": overall(components, lifecycle), "lifecycle": lifecycle, "components": components, "logs": logs}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["overall_state"] == "ready" else 3


if __name__ == "__main__":
    raise SystemExit(main())
