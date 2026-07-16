# Fresh-host reproduction guide

This is the end-to-end delivery path for a new AI Max, Server PC, or TurtleBot3
host. Run only the commands for the local role unless a step explicitly gives a
deployment order.

## 1. Prepare the host

1. Match the OS, architecture, Docker/Compose, ROS base, and host packages in
   [prerequisites.md](prerequisites.md).
2. Restore external assets outside Git: llama.cpp/Qwen GGUF on AI Max and
   SenseVoiceSmall on Server PC. Verify the recorded sizes and SHA-256 values.
3. Connect the role to the required subnets, synchronize NTP, and reserve the
   documented service ports.
4. On TB3, connect OpenCR, LDS-02, camera, microphone, speaker, and display
   before the install preflight. See [hardware.md](hardware.md).

## 2. Clone and configure

Clone the repository directly into the configured role path. Runtime hosts use
the read-only deploy-key procedure in
[prerequisites.md](prerequisites.md#read-only-github-deploy-key-over-port-443).

```bash
git clone git@github.com:r1file/tb3-multimodal-interaction.git REPO_PATH
cd REPO_PATH
cp .env.example .env
chmod 600 .env
```

Edit `.env` for this host only. Confirm addresses, ports, repository/workspace
paths, model paths, ROS domain, device paths, ALSA names, display, and
`TB3_BEHAVIOR_DRY_RUN=true`. Never commit `.env`.

## 3. Validate repository and install readiness

```bash
bash scripts/validate_repository.sh
bash deploy/preflight.sh <ai_max|server_pc|tb3> --phase install
```

Fix every `FAIL`. Warnings must be understood and recorded; a failed preflight
is not bypassed by starting containers manually.

## 4. Install role configuration

```bash
bash deploy/role.sh <role> install
```

Install writes only the role-owned Compose/UI/runtime configuration described in
[deployment.md](deployment.md). Timestamped backups are retained where existing
host files are replaced.

## 5. Start and verify in order

Start AI Max, then Server PC, then TB3. After each start, require both role
status and runtime preflight to report ready/pass.

```bash
bash deploy/role.sh <role> start
bash deploy/role.sh <role> status
bash deploy/preflight.sh <role> --phase runtime
```

After TB3 is ready, run the full health check inside the ROS container:

```bash
docker exec turtlebot3 bash -lc \
  'source /opt/ros/jazzy/setup.bash && source /workspace/ros2_ws/install/setup.bash && bash /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/health_check_full.sh full'
```

Verify the four HTTP endpoints listed in [deployment.md](deployment.md). Keep
motion in dry-run until a separate physical-safety acceptance.

## 6. Routine update

```bash
git status --short
git pull --ff-only
bash scripts/validate_repository.sh
bash deploy/role.sh <role> restart
bash deploy/role.sh <role> status
```

If `git status` shows host source edits, stop. Preserve the diff and restore the
machine-specific value to `.env` or another documented external location before
pulling.

## 7. Stop

Stop in reverse deployment order: TB3, Server PC, AI Max.

```bash
bash deploy/role.sh <role> stop
bash deploy/role.sh <role> status
```

The stop action preserves models, repositories, logs, state markers, and
backups.

## 8. Roll back

Do not overwrite a running role. First capture status and logs, stop the affected
role, and verify the backup read-only. Follow [rollback.md](rollback.md) exactly.
Rollback archives are external assets and are never fetched from Git.

## Reproduction evidence

Record the Git commit, `.env` checksum with secrets excluded, preflight output,
build/test result, role startup time, final status JSON, and full-health trace.
The release checklist defines which evidence is required before a tag.
