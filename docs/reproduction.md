# Fresh-host reproduction guide

The deployment unit is one reviewed Git commit plus one unchanged three-host
manifest. Run role-local commands only on the matching host.

## 1. Prepare hosts and external assets

1. Match the supported OS, architecture, Docker/Compose and packages in
   [prerequisites.md](prerequisites.md).
2. Restore llama.cpp and Qwen GGUF/mmproj on AI Max, and SenseVoiceSmall on
   Server PC. Keep these assets outside Git and verify their recorded hashes.
3. Configure routing, service ports and NTP. Connect OpenCR, LiDAR, camera,
   microphone, speaker and display on TB3.

## 2. Create one manifest

On an administration machine, copy the template outside the checkout. Fill all
three role tables and pin the full reviewed commit SHA. The manifest contains
topology and host paths, not credentials.

```bash
cp config/host-manifest.example.toml /secure/deploy/tb3-release.toml
git rev-parse HEAD
# Set [release].commit to that exact SHA.
python3 deploy/host_manifest.py validate \
  --manifest /secure/deploy/tb3-release.toml
sha256sum /secure/deploy/tb3-release.toml
```

Copy this exact file to every host. Do not create per-host variants: all role
tables remain together and the SHA-256 must match on all three machines.

## 3. Clone the same artifact on every host

Clone into that role's `repo_dir`, then detach at the manifest commit. Runtime
hosts may use the read-only deploy-key procedure in
[prerequisites.md](prerequisites.md#read-only-github-deploy-key-over-port-443).

```bash
git clone git@github.com:r1file/tb3-multimodal-interaction.git REPO_PATH
git -C REPO_PATH fetch --prune origin
git -C REPO_PATH checkout --detach RELEASE_COMMIT
test "$(git -C REPO_PATH rev-parse HEAD)" = "RELEASE_COMMIT"
```

## 4. Validate and install

```bash
bash scripts/validate_repository.sh
bash deploy/preflight.sh <ai_max|server_pc|tb3> \
  --phase install --manifest /secure/deploy/tb3-release.toml
bash deploy/role.sh <role> install \
  --manifest /secure/deploy/tb3-release.toml
```

Fix every `FAIL`. Install renders role-owned Compose/UI files and, on ROS hosts,
the Fast DDS peer profile derived from the manifest. Replaced files receive a
timestamped backup.

## 5. Start and verify in order

Start AI Max, Server PC, then TB3. After each start, require both status and
runtime preflight to pass.

```bash
bash deploy/role.sh <role> start --manifest /secure/deploy/tb3-release.toml
bash deploy/role.sh <role> status --manifest /secure/deploy/tb3-release.toml
bash deploy/preflight.sh <role> --phase runtime \
  --manifest /secure/deploy/tb3-release.toml
```

Status JSON records `manifest_id`, manifest SHA-256 and release commit. After
TB3 is ready, run `scripts/health_check_full.sh full` inside the configured ROS
container. Keep motion in dry-run until a separate physical-safety acceptance.

## 6. Update or roll back

A new commit requires a new reviewed manifest identity. Stop in reverse order,
fetch the exact commit, validate the new manifest on every host, reinstall, and
start in normal order. Never pull over host-edited source. Follow
[rollback.md](rollback.md) if the verified commit cannot restart.

## Reproduction evidence

Record the Git commit, identical manifest SHA-256 from all three hosts,
repository validation, install/runtime preflight output, startup duration,
final status JSON and full-health trace.
