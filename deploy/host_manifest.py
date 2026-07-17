#!/usr/bin/env python3
"""Validate one three-host manifest and export role-specific runtime settings."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


SCHEMA_VERSION = 1
ROLES = ("ai_max", "server_pc", "tb3")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TEMPLATE_COMMIT = "REPLACE_WITH_RELEASE_COMMIT"
DOCUMENTATION_NETWORKS = tuple(
    ipaddress.ip_network(value) for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except FileNotFoundError as exc:
        raise ManifestError(f"host manifest does not exist: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("host manifest root must be a TOML table")
    return data


def field(data: dict, section: str, key: str, expected_type: type):
    table = data.get(section)
    if not isinstance(table, dict):
        raise ManifestError(f"missing [{section}] table")
    if key not in table:
        raise ManifestError(f"missing [{section}].{key}")
    value = table[key]
    if expected_type is int and isinstance(value, bool):
        raise ManifestError(f"[{section}].{key} must be an integer")
    if not isinstance(value, expected_type):
        raise ManifestError(f"[{section}].{key} must be {expected_type.__name__}")
    if expected_type is str and not value.strip():
        raise ManifestError(f"[{section}].{key} must not be empty")
    return value


def absolute_path(data: dict, section: str, key: str) -> str:
    value = field(data, section, key, str)
    if not Path(value).is_absolute():
        raise ManifestError(f"[{section}].{key} must be an absolute path: {value}")
    return value


def repository_identity(value: str) -> str:
    """Normalize common SSH/HTTPS Git remotes to an owner/repository identity."""
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if "://" in normalized:
        normalized = normalized.split("://", 1)[1]
        normalized = normalized.split("@", 1)[-1]
        normalized = normalized.split("/", 1)[-1]
    elif ":" in normalized:
        normalized = normalized.split(":", 1)[1]
    return normalized.strip("/")


def placeholder_paths(value, prefix="") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(placeholder_paths(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, str) and "REPLACE" in value.upper():
        found.append(prefix)
    return found


def validate_manifest(
    data: dict,
    *,
    role: str | None = None,
    allow_template: bool = False,
    repo_root: Path | None = None,
    require_clean: bool = False,
) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")
    placeholders = placeholder_paths(data)
    if placeholders and not allow_template:
        raise ManifestError(f"template placeholders remain: {', '.join(placeholders)}")
    manifest_id = field(data, "release", "manifest_id", str)
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", manifest_id):
        raise ManifestError("[release].manifest_id may contain only letters, numbers, dot, underscore, and dash")
    repository = field(data, "release", "repository", str)
    if "/" not in repository_identity(repository):
        raise ManifestError("[release].repository must identify an owner/repository Git remote")
    commit = field(data, "release", "commit", str)
    if commit == TEMPLATE_COMMIT and allow_template:
        pass
    elif not COMMIT_RE.fullmatch(commit):
        raise ManifestError("[release].commit must be the full immutable 40-character Git commit")

    addresses = []
    for key in ("ai_max_ip", "server_pc_ip", "tb3_ip"):
        value = field(data, "network", key, str)
        try:
            address = ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError as exc:
            raise ManifestError(f"[network].{key} must be an IPv4 address: {value}") from exc
        if any(address in network for network in DOCUMENTATION_NETWORKS) and not allow_template:
            raise ManifestError(f"[network].{key} still uses a documentation-only address: {value}")
        addresses.append(value)
    if len(set(addresses)) != len(addresses):
        raise ManifestError("all three role addresses must be unique")
    for key in ("vlm_port", "vlm_dashboard_port", "server_dashboard_port", "tb3_ui_port"):
        value = field(data, "network", key, int)
        if not 1 <= value <= 65535:
            raise ManifestError(f"[network].{key} must be between 1 and 65535")
    if field(data, "network", "vlm_port", int) == field(data, "network", "vlm_dashboard_port", int):
        raise ManifestError("AI Max VLM and dashboard ports must be different")

    domain_id = field(data, "ros", "domain_id", int)
    if not 0 <= domain_id <= 232:
        raise ManifestError("[ros].domain_id must be between 0 and 232")
    discovery = field(data, "ros", "automatic_discovery_range", str)
    if discovery not in {"SUBNET", "LOCALHOST", "OFF", "SYSTEM_DEFAULT"}:
        raise ManifestError("[ros].automatic_discovery_range is not supported")
    port_start = field(data, "ros", "peer_port_start", int)
    port_end = field(data, "ros", "peer_port_end", int)
    if not (1 <= port_start <= port_end <= 65535) or port_end - port_start > 128:
        raise ManifestError("[ros] peer port range must be ordered, valid, and at most 129 ports")
    container_profile = absolute_path(data, "ros", "container_fastdds_profile")
    if not container_profile.startswith("/workspace/"):
        raise ManifestError("[ros].container_fastdds_profile must be inside /workspace")

    field(data, "runtime", "log_retention_days", int)
    field(data, "runtime", "log_retain_files", int)
    field(data, "runtime", "startup_grace_s", int)
    if min(
        field(data, "runtime", "log_retention_days", int),
        field(data, "runtime", "log_retain_files", int),
        field(data, "runtime", "startup_grace_s", int),
    ) <= 0:
        raise ManifestError("[runtime] values must be positive")
    for key in ("status_stale_s", "dashboard_timeout_s", "status_relay_interval_s"):
        value = data.get("runtime", {}).get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0:
            raise ManifestError(f"[runtime].{key} must be a positive number")
    for key in ("robotis_base_image", "ai_dashboard_base_image"):
        image = field(data, "runtime", key, str)
        if not re.search(r"@sha256:[0-9a-f]{64}$", image):
            raise ManifestError(f"[runtime].{key} must be pinned by sha256 digest")
    field(data, "runtime", "robotis_repository", str)
    if not COMMIT_RE.fullmatch(field(data, "runtime", "robotis_commit", str)):
        raise ManifestError("[runtime].robotis_commit must be a full 40-character Git commit")
    field(data, "runtime", "ntp_required", bool)

    if role is not None and role not in ROLES:
        raise ManifestError(f"unknown role: {role}")
    # Every role consumes the same manifest, so a partial role-local manifest is
    # never valid even when only one role is being started.
    for selected in ROLES:
        absolute_path(data, selected, "repo_dir")
        absolute_path(data, selected, "runtime_log_dir")
        if selected == "ai_max":
            for key in ("root_dir", "llama_cpp_dir", "llama_server", "model_path", "mmproj_path"):
                absolute_path(data, selected, key)
            field(data, selected, "llama_cpp_repository", str)
            if not COMMIT_RE.fullmatch(field(data, selected, "llama_cpp_commit", str)):
                raise ManifestError("[ai_max].llama_cpp_commit must be a full 40-character Git commit")
            for key in ("model_sha256", "mmproj_sha256"):
                if not re.fullmatch(r"[0-9a-f]{64}", field(data, selected, key, str)):
                    raise ManifestError(f"[ai_max].{key} must be a SHA-256 digest")
            field(data, selected, "model", str)
            field(data, selected, "context_size", int)
            field(data, selected, "gpu_layers", int)
            field(data, selected, "wait_timeout_s", int)
            if min(
                field(data, selected, "context_size", int),
                field(data, selected, "wait_timeout_s", int),
            ) <= 0 or field(data, selected, "gpu_layers", int) < 0:
                raise ManifestError("[ai_max] context/wait must be positive and gpu_layers non-negative")
            field(data, selected, "dashboard_image", str)
            field(data, selected, "dashboard_container", str)
            continue

        workspace = Path(absolute_path(data, selected, "ros_workspace_dir"))
        repo_dir = Path(absolute_path(data, selected, "repo_dir"))
        runtime_log = Path(absolute_path(data, selected, "runtime_log_dir"))
        try:
            repo_dir.relative_to(workspace / "ros2_ws" / "src")
        except ValueError as exc:
            raise ManifestError(
                f"[{selected}].repo_dir must be inside [{selected}].ros_workspace_dir/ros2_ws/src"
            ) from exc
        try:
            runtime_log.relative_to(workspace)
        except ValueError as exc:
            raise ManifestError(
                f"[{selected}].runtime_log_dir must be inside [{selected}].ros_workspace_dir"
            ) from exc
        for key in ("compose_dir", "robotis_repo_dir"):
            absolute_path(data, selected, key)
        for key in ("ros_container", "ros_image", "turtlebot3_model", "lidar_model"):
            field(data, selected, key, str)

        if selected == "server_pc":
            absolute_path(data, selected, "sensevoice_model_dir")
            if not re.fullmatch(r"[0-9a-f]{64}", field(data, selected, "sensevoice_model_sha256", str)):
                raise ManifestError("[server_pc].sensevoice_model_sha256 must be a SHA-256 digest")
            field(data, selected, "asr_container", str)
            field(data, selected, "tts_container", str)
            field(data, selected, "asr_image", str)
            field(data, selected, "tts_image", str)
        else:
            absolute_path(data, selected, "home_dir")
            for key in ("camera_device", "opencr_device", "lidar_device"):
                absolute_path(data, selected, key)
            for key in (
                "mic_alsa_device", "speaker_alsa_device", "display", "xorg_vt",
                "cmd_vel_topic", "cmd_vel_candidates",
            ):
                field(data, selected, key, str)
            if not re.fullmatch(r":\d+(?:\.\d+)?", data[selected]["display"]):
                raise ManifestError("[tb3].display must use X display syntax such as :0")
            if not re.fullmatch(r"vt\d+", data[selected]["xorg_vt"]):
                raise ManifestError("[tb3].xorg_vt must use syntax such as vt1")
            candidates = [item.strip() for item in data[selected]["cmd_vel_candidates"].split(",")]
            if not candidates or any(not item.startswith("/") for item in candidates):
                raise ManifestError("[tb3].cmd_vel_candidates must be a comma-separated list of absolute ROS topics")
            if data[selected]["cmd_vel_topic"] != "auto" and not data[selected]["cmd_vel_topic"].startswith("/"):
                raise ManifestError("[tb3].cmd_vel_topic must be 'auto' or an absolute ROS topic")
            field(data, selected, "behavior_dry_run", bool)
            max_duration = data[selected].get("behavior_max_duration")
            if not isinstance(max_duration, (int, float)) or isinstance(max_duration, bool):
                raise ManifestError("[tb3].behavior_max_duration must be a number")
            if not 0 < float(max_duration) <= 10:
                raise ManifestError("[tb3].behavior_max_duration must be in (0, 10]")
            motion_gap = data[selected].get("behavior_motion_gap_s")
            if not isinstance(motion_gap, (int, float)) or isinstance(motion_gap, bool):
                raise ManifestError("[tb3].behavior_motion_gap_s must be a number")
            if not 0 < float(motion_gap) <= 1:
                raise ManifestError("[tb3].behavior_motion_gap_s must be in (0, 1]")

    if repo_root is not None and commit != TEMPLATE_COMMIT:
        try:
            actual = subprocess.check_output(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ManifestError(f"cannot read Git commit from {repo_root}") from exc
        if actual != commit:
            raise ManifestError(
                f"release commit mismatch: manifest={commit}, checkout={actual}; deploy one immutable artifact"
            )
        try:
            actual_remote = subprocess.check_output(
                ["git", "-C", str(repo_root), "remote", "get-url", "origin"], text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ManifestError(f"cannot read origin remote from {repo_root}") from exc
        if repository_identity(actual_remote) != repository_identity(repository):
            raise ManifestError(
                "release repository mismatch: "
                f"manifest={repository_identity(repository)}, checkout={repository_identity(actual_remote)}"
            )
        if require_clean:
            try:
                dirty = subprocess.check_output(
                    ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=normal"],
                    text=True,
                ).strip()
            except (OSError, subprocess.CalledProcessError) as exc:
                raise ManifestError(f"cannot inspect checkout state at {repo_root}") from exc
            if dirty:
                raise ManifestError("checkout has local changes; runtime requires the exact immutable release artifact")
        if role is not None:
            configured_repo = Path(field(data, role, "repo_dir", str)).resolve()
            if repo_root.resolve() != configured_repo:
                raise ManifestError(
                    f"checkout path mismatch for {role}: manifest={configured_repo}, actual={repo_root.resolve()}"
                )


def manifest_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def container_runtime_path(data: dict, role: str) -> str:
    workspace = Path(field(data, role, "ros_workspace_dir", str))
    runtime_log = Path(field(data, role, "runtime_log_dir", str))
    relative = runtime_log.relative_to(workspace)
    return str(Path("/workspace") / relative)


def environment(data: dict, role: str, manifest_path: Path) -> dict[str, str]:
    network = data["network"]
    ros = data["ros"]
    runtime = data["runtime"]
    selected = data[role]
    values: dict[str, object] = {
        "TB3_HOST_MANIFEST": str(manifest_path.resolve()),
        "TB3_MANIFEST_SCHEMA": data["schema_version"],
        "TB3_MANIFEST_ID": data["release"]["manifest_id"],
        "TB3_MANIFEST_SHA256": manifest_fingerprint(manifest_path),
        "RELEASE_COMMIT": data["release"]["commit"],
        "TB3_ROLE": role,
        "AI_MAX_IP": network["ai_max_ip"],
        "SERVER_PC_IP": network["server_pc_ip"],
        "TB3_IP": network["tb3_ip"],
        "VLM_PORT": network["vlm_port"],
        "VLM_DASHBOARD_PORT": network["vlm_dashboard_port"],
        "SERVER_DASHBOARD_PORT": network["server_dashboard_port"],
        "TB3_UI_PORT": network["tb3_ui_port"],
        "ROS_DOMAIN_ID": ros["domain_id"],
        "ROS_AUTOMATIC_DISCOVERY_RANGE": ros["automatic_discovery_range"],
        "FASTDDS_PEER_PORT_START": ros["peer_port_start"],
        "FASTDDS_PEER_PORT_END": ros["peer_port_end"],
        "TB3_FASTDDS_PROFILE": ros["container_fastdds_profile"],
        "NTP_REQUIRED": runtime["ntp_required"],
        "RUNTIME_LOG_RETENTION_DAYS": runtime["log_retention_days"],
        "RUNTIME_LOG_RETAIN_FILES": runtime["log_retain_files"],
        "ROLE_STARTUP_GRACE_S": runtime["startup_grace_s"],
        "ROLE_STATUS_STALE_S": runtime["status_stale_s"],
        "ROLE_DASHBOARD_TIMEOUT_S": runtime["dashboard_timeout_s"],
        "STATUS_RELAY_INTERVAL_S": runtime["status_relay_interval_s"],
        "ROBOTIS_BASE_IMAGE": runtime["robotis_base_image"],
        "AI_DASHBOARD_BASE_IMAGE": runtime["ai_dashboard_base_image"],
        "ROBOTIS_REPOSITORY": runtime["robotis_repository"],
        "ROBOTIS_COMMIT": runtime["robotis_commit"],
        "VLM_BASE_URL": f"http://{network['ai_max_ip']}:{network['vlm_port']}",
        "VLM_MODEL": data["ai_max"]["model"],
    }
    if role == "ai_max":
        values.update({
            "AI_MAX_ROOT": selected["root_dir"],
            "AI_MAX_REPO_DIR": selected["repo_dir"],
            "LLAMA_CPP_DIR": selected["llama_cpp_dir"],
            "LLAMA_SERVER": selected["llama_server"],
            "VLM_MODEL": selected["model"],
            "VLM_MODEL_PATH": selected["model_path"],
            "VLM_MMPROJ_PATH": selected["mmproj_path"],
            "VLM_MODEL_SHA256": selected["model_sha256"],
            "VLM_MMPROJ_SHA256": selected["mmproj_sha256"],
            "LLAMA_CPP_REPOSITORY": selected["llama_cpp_repository"],
            "LLAMA_CPP_COMMIT": selected["llama_cpp_commit"],
            "VLM_CONTEXT_SIZE": selected["context_size"],
            "VLM_GPU_LAYERS": selected["gpu_layers"],
            "VLM_WAIT_TIMEOUT_S": selected["wait_timeout_s"],
            "AI_MAX_RUNTIME_LOG_DIR": selected["runtime_log_dir"],
            "AI_DASHBOARD_IMAGE": selected["dashboard_image"],
            "AI_DASHBOARD_CONTAINER": selected["dashboard_container"],
        })
    else:
        container_runtime = container_runtime_path(data, role)
        values.update({
            "ROS_CONTAINER": selected["ros_container"],
            "ROS_IMAGE": selected["ros_image"],
            "ROS_WORKSPACE_DIR": selected["ros_workspace_dir"],
            "ROBOTIS_REPO_DIR": selected["robotis_repo_dir"],
            "TURTLEBOT3_MODEL": selected["turtlebot3_model"],
            "LDS_MODEL": selected["lidar_model"],
            "CONTAINER_RUNTIME_LOG_DIR": container_runtime,
            "HOST_FASTDDS_PROFILE": str(Path(selected["runtime_log_dir"]) / "fastdds_initial_peers.xml"),
        })
        if role == "server_pc":
            values.update({
                "SERVER_COMPOSE_DIR": selected["compose_dir"],
                "SERVER_REPO_DIR": selected["repo_dir"],
                "SERVER_RUNTIME_LOG_DIR": selected["runtime_log_dir"],
                "SENSEVOICE_MODEL_DIR": selected["sensevoice_model_dir"],
                "SENSEVOICE_MODEL_SHA256": selected["sensevoice_model_sha256"],
                "ASR_CONTAINER": selected["asr_container"],
                "TTS_CONTAINER": selected["tts_container"],
                "ASR_IMAGE": selected["asr_image"],
                "TTS_IMAGE": selected["tts_image"],
            })
        else:
            values.update({
                "TB3_COMPOSE_DIR": selected["compose_dir"],
                "TB3_REPO_DIR": selected["repo_dir"],
                "TB3_RUNTIME_LOG_DIR": selected["runtime_log_dir"],
                "TB3_HOME_DIR": selected["home_dir"],
                "TB3_CAMERA_DEVICE": selected["camera_device"],
                "TB3_OPENCR_DEVICE": selected["opencr_device"],
                "TB3_LIDAR_DEVICE": selected["lidar_device"],
                "TB3_MIC_ALSA_DEVICE": selected["mic_alsa_device"],
                "TB3_SPEAKER_ALSA_DEVICE": selected["speaker_alsa_device"],
                "TB3_DISPLAY": selected["display"],
                "TB3_UI_XORG_VT": selected["xorg_vt"],
                "TB3_CMD_VEL_TOPIC": selected["cmd_vel_topic"],
                "TB3_CMD_VEL_CANDIDATES": selected["cmd_vel_candidates"],
                "TB3_BEHAVIOR_DRY_RUN": selected["behavior_dry_run"],
                "TB3_BEHAVIOR_MAX_DURATION": selected["behavior_max_duration"],
                "TB3_BEHAVIOR_MOTION_GAP_S": selected["behavior_motion_gap_s"],
            })
    return {key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in values.items()}


def fastdds_xml(data: dict) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        '<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">',
        '  <participant profile_name="tb3_manifest_initial_peers" is_default_profile="true">',
        '    <rtps>',
        '      <builtin>',
        '        <initialPeersList>',
    ]
    for address in (data["network"]["server_pc_ip"], data["network"]["tb3_ip"]):
        for port in range(data["ros"]["peer_port_start"], data["ros"]["peer_port_end"] + 1):
            lines.append(
                f"          <locator><udpv4><address>{address}</address><port>{port}</port></udpv4></locator>"
            )
    lines.extend([
        '        </initialPeersList>',
        '      </builtin>',
        '    </rtps>',
        '  </participant>',
        '</profiles>',
        '',
    ])
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "export-shell", "render-fastdds", "show"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--allow-template", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = load_manifest(args.manifest)
        validate_manifest(
            data,
            role=args.role,
            allow_template=args.allow_template,
            repo_root=args.repo_root,
            require_clean=args.require_clean,
        )
        if args.command == "validate":
            print(
                f"HOST_MANIFEST_VALID id={data['release']['manifest_id']} "
                f"sha256={manifest_fingerprint(args.manifest)} role={args.role or 'all'}"
            )
        elif args.command == "export-shell":
            if not args.role:
                raise ManifestError("export-shell requires --role")
            for key, value in environment(data, args.role, args.manifest).items():
                print(f"export {key}={shlex.quote(value)}")
        elif args.command == "render-fastdds":
            content = fastdds_xml(data)
            if args.output:
                atomic_write(args.output, content)
                print(f"FASTDDS_PROFILE_WRITTEN path={args.output}")
            else:
                sys.stdout.write(content)
        else:
            safe = {
                "manifest_id": data["release"]["manifest_id"],
                "commit": data["release"]["commit"],
                "role": args.role,
                "fingerprint": manifest_fingerprint(args.manifest),
            }
            print(json.dumps(safe, sort_keys=True))
    except ManifestError as exc:
        print(f"HOST_MANIFEST_INVALID: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
