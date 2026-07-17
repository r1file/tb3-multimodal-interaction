from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "deploy" / "host_manifest.py"
EXAMPLE = ROOT / "config" / "host-manifest.example.toml"


def configured_manifest(tmp_path: Path, *, server_ip="10.20.0.20", tb3_ip="10.20.0.30") -> Path:
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    text = EXAMPLE.read_text(encoding="utf-8")
    text = text.replace("REPLACE_WITH_RELEASE_COMMIT", commit)
    text = text.replace("REPLACE_WITH_MANIFEST_ID", "test-release")
    text = text.replace("REPLACE_CAMERA", "video-test")
    text = text.replace("REPLACE_OPENCR", "opencr-test")
    text = text.replace("REPLACE_LIDAR", "lidar-test")
    text = text.replace("REPLACE_MIC", "MicTest")
    text = text.replace("REPLACE_SPEAKER", "SpeakerTest")
    text = text.replace("192.0.2.10", "10.10.0.10")
    text = text.replace("192.0.2.20", server_ip)
    text = text.replace("192.0.2.30", tb3_ip)
    text = text.replace(
        'repo_dir = "/srv/tb3/ai/repo"',
        f'repo_dir = "{ROOT}"',
    )
    for role, old_workspace, old_repo, old_runtime in (
        (
            "server_pc",
            "/srv/tb3/server-workspace",
            "/srv/tb3/server-workspace/ros2_ws/src/tb3_multimodal_interaction",
            "/srv/tb3/server-workspace/runtime_logs/tb3_multimodal_interaction",
        ),
        (
            "tb3",
            "/srv/tb3/robot-workspace",
            "/srv/tb3/robot-workspace/ros2_ws/src/tb3_multimodal_interaction",
            "/srv/tb3/robot-workspace/runtime_logs/tb3_multimodal_interaction",
        ),
    ):
        workspace = tmp_path / f"{role}-workspace"
        repo_link = workspace / "ros2_ws" / "src" / "tb3_multimodal_interaction"
        repo_link.parent.mkdir(parents=True)
        repo_link.symlink_to(ROOT, target_is_directory=True)
        runtime = workspace / "runtime_logs" / "tb3_multimodal_interaction"
        text = text.replace(f'ros_workspace_dir = "{old_workspace}"', f'ros_workspace_dir = "{workspace}"')
        text = text.replace(f'repo_dir = "{old_repo}"', f'repo_dir = "{repo_link}"')
        text = text.replace(f'runtime_log_dir = "{old_runtime}"', f'runtime_log_dir = "{runtime}"')
    path = tmp_path / "host-manifest.toml"
    path.write_text(text, encoding="utf-8")
    return path


def run_cli(*args: str, check=True):
    return subprocess.run(
        ["python3", str(CLI), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def role_repo(tmp_path: Path, role: str) -> Path:
    if role == "ai_max":
        return ROOT
    return tmp_path / f"{role}-workspace" / "ros2_ws" / "src" / "tb3_multimodal_interaction"


def test_example_schema_is_valid_as_template():
    result = run_cli("validate", "--manifest", str(EXAMPLE), "--allow-template")
    assert "HOST_MANIFEST_VALID" in result.stdout


def test_one_manifest_exports_all_roles_and_pins_checkout(tmp_path):
    manifest = configured_manifest(tmp_path)
    for role in ("ai_max", "server_pc", "tb3"):
        result = run_cli(
            "export-shell",
            "--manifest", str(manifest),
            "--role", role,
            "--repo-root", str(role_repo(tmp_path, role)),
        )
        assert f"export TB3_ROLE={role}" in result.stdout
        assert "export RELEASE_COMMIT=" in result.stdout
        assert "export TB3_MANIFEST_SHA256=" in result.stdout
        assert "192.168." not in result.stdout
    server = run_cli(
        "export-shell", "--manifest", str(manifest), "--role", "server_pc", "--repo-root", str(role_repo(tmp_path, "server_pc"))
    ).stdout
    assert "export ROS_CONTAINER=tb3-server-ros" in server
    assert "export ROS_DOMAIN_ID=30" in server
    assert "export ASR_IMAGE=ros-cui/turtlebot3:jazzy-asr" in server
    assert "export ROLE_STATUS_STALE_S=30" in server
    assert "export ROBOTIS_COMMIT=da785b7201d317e6e2a662e41bb3d3fd50ebd503" in server
    assert "export SENSEVOICE_MODEL_SHA256=833ca2dcfdf8ec91bd4f31cfac36d6124e0c459074d5e909aec9cabe6204a3ea" in server
    assert "export TB3_FASTDDS_PROFILE=/workspace/runtime_logs/tb3_multimodal_interaction/fastdds_initial_peers.xml" in server
    tb3 = run_cli(
        "export-shell", "--manifest", str(manifest), "--role", "tb3", "--repo-root", str(role_repo(tmp_path, "tb3"))
    ).stdout
    assert "export TB3_BEHAVIOR_MAX_DURATION=1.5" in tb3
    assert "export TB3_DISPLAY=:0" in tb3
    assert "export TB3_CMD_VEL_TOPIC=auto" in tb3


def test_fastdds_is_generated_from_manifest_network(tmp_path):
    manifest = configured_manifest(tmp_path, server_ip="172.20.1.4", tb3_ip="172.20.1.9")
    output = tmp_path / "runtime" / "fastdds.xml"
    run_cli(
        "render-fastdds",
        "--manifest", str(manifest),
        "--role", "server_pc",
        "--repo-root", str(role_repo(tmp_path, "server_pc")),
        "--output", str(output),
    )
    text = output.read_text(encoding="utf-8")
    assert "172.20.1.4" in text
    assert "172.20.1.9" in text
    assert "192.168." not in text
    assert text.count("<locator>") == 40


def test_release_commit_mismatch_is_rejected(tmp_path):
    manifest = configured_manifest(tmp_path)
    text = manifest.read_text(encoding="utf-8")
    current = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    text = text.replace(current, "0" * 40)
    manifest.write_text(text, encoding="utf-8")
    result = run_cli(
        "validate",
        "--manifest", str(manifest),
        "--role", "tb3",
        "--repo-root", str(role_repo(tmp_path, "tb3")),
        check=False,
    )
    assert result.returncode == 2
    assert "release commit mismatch" in result.stderr


def test_repository_identity_mismatch_is_rejected(tmp_path):
    manifest = configured_manifest(tmp_path)
    text = manifest.read_text(encoding="utf-8").replace(
        "git@github.com:r1file/tb3-multimodal-interaction.git",
        "git@github.com:someone-else/another-repository.git",
    )
    manifest.write_text(text, encoding="utf-8")
    result = run_cli(
        "validate", "--manifest", str(manifest), "--role", "ai_max",
        "--repo-root", str(ROOT), check=False,
    )
    assert result.returncode == 2
    assert "release repository mismatch" in result.stderr


def test_role_local_start_rejects_partial_three_host_manifest(tmp_path):
    manifest = configured_manifest(tmp_path)
    text = manifest.read_text(encoding="utf-8")
    text = text[:text.index("\n[tb3]\n")]
    manifest.write_text(text, encoding="utf-8")
    result = run_cli(
        "validate", "--manifest", str(manifest), "--role", "server_pc",
        "--repo-root", str(role_repo(tmp_path, "server_pc")), check=False,
    )
    assert result.returncode == 2
    assert "missing [tb3]" in result.stderr


def test_missing_manifest_fails_before_lifecycle_action():
    result = subprocess.run(
        ["bash", str(ROOT / "deploy" / "role.sh"), "ai_max", "status", "--manifest", "/nonexistent/host.toml"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "Missing host manifest" in result.stderr


def test_canonical_loader_requires_clean_release_checkout():
    loader = (ROOT / "deploy" / "lib" / "load_env.sh").read_text(encoding="utf-8")
    assert "--require-clean" in loader


def test_runtime_has_no_lab_host_defaults():
    roots = ["deploy", "scripts", "launch", "ai_max_vlm_server", "tb3_multimodal_interaction"]
    offenders = []
    for root_name in roots:
        for path in (ROOT / root_name).rglob("*"):
            if not path.is_file() or path.suffix in {".pyc", ".md"} or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in ("192.168.64.246", "192.168.250.30", "192.168.250.10")):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_manifest_values_reach_canonical_runtime():
    behavior = (ROOT / "scripts" / "start_behavior_executor_host.sh").read_text(encoding="utf-8")
    assert "-p max_duration:='$MAX_DURATION'" in behavior
    assert "-p motion_gap_sec:='$MOTION_GAP'" in behavior
    touch = (ROOT / "scripts" / "start_touch_gui_host.sh").read_text(encoding="utf-8")
    assert '-- Xorg "$DISPLAY_VALUE" "$XORG_VT"' in touch
    assert "Xorg :0" not in touch
    face = (ROOT / "tb3_multimodal_interaction" / "face_display_node.py").read_text(encoding="utf-8")
    assert "Path(self.camera_device).exists()" in face
    assert "Path('/dev/video0').exists()" not in face
    compose = (ROOT / "deploy" / "tb3" / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    for variable in ("ROS_CONTAINER", "ROS_WORKSPACE_DIR", "ROBOTIS_REPO_DIR", "ROS_DOMAIN_ID", "TB3_DISPLAY"):
        assert "${" + variable + "}" in compose
    role_status = (ROOT / "deploy" / "role_status.py").read_text(encoding="utf-8")
    for variable in ("TB3_MANIFEST_ID", "TB3_MANIFEST_SHA256", "RELEASE_COMMIT"):
        assert f'os.environ["{variable}"]' in role_status
    readiness = (ROOT / "scripts" / "check_tb3_bringup_graph.py").read_text(encoding="utf-8")
    health = (ROOT / "scripts" / "health_check_full.sh").read_text(encoding="utf-8")
    assert 'os.environ["TB3_CMD_VEL_CANDIDATES"]' in readiness
    assert 'TB3_CMD_VEL_CANDIDATES:?' in health
    for dockerfile in (
        ROOT / "deploy" / "server_pc" / "docker" / "Dockerfile.av-tools",
        ROOT / "deploy" / "tb3" / "docker" / "Dockerfile.av-tools",
        ROOT / "ai_max_vlm_server" / "dashboard" / "Dockerfile",
    ):
        text = dockerfile.read_text(encoding="utf-8")
        assert ":latest" not in text
        assert "FROM ${" in text


def test_generated_role_environment_renders_compose(tmp_path):
    if not shutil.which("docker"):
        return
    manifest = configured_manifest(tmp_path)
    for role, compose_rel in (
        ("server_pc", "deploy/server_pc/docker/docker-compose.yml"),
        ("tb3", "deploy/tb3/docker/docker-compose.yml"),
    ):
        env = os.environ.copy()
        env.update({
            "MANIFEST": str(manifest),
            "ROLE": role,
            "ROLE_REPO": str(role_repo(tmp_path, role)),
            "COMPOSE": str(ROOT / compose_rel),
        })
        result = subprocess.run(
            [
                "bash", "-c",
                'eval "$(python3 \"$ROLE_REPO/deploy/host_manifest.py\" export-shell '
                '--manifest \"$MANIFEST\" --role \"$ROLE\" --repo-root \"$ROLE_REPO\")"; '
                'docker compose -f "$COMPOSE" config',
            ],
            text=True,
            capture_output=True,
            env=env,
            check=True,
        )
        assert "${" not in result.stdout
        expected = "tb3-server-ros" if role == "server_pc" else "tb3-robot-ros"
        assert f"container_name: {expected}" in result.stdout
