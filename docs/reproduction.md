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

On an administration machine, initialize the template outside the checkout.
Fill all three role tables and pin the full reviewed commit SHA. The manifest
contains topology and host paths, not credentials.

```bash
bash deploy/role.sh manifest-init
git rev-parse HEAD
# Set [release].commit to that exact SHA.
python3 deploy/host_manifest.py validate \
  --manifest ~/.config/tb3/host-manifest.toml
sha256sum ~/.config/tb3/host-manifest.toml
```

`manifest-init` creates the parent directory with private permissions when
needed, writes the template as mode `0600`, and refuses to overwrite an existing
file. Copy this exact completed file to `~/.config/tb3/host-manifest.toml` on
every host. Do not run separate edits on each host: all role tables remain
together and the SHA-256 must match.

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
  --phase install
bash deploy/role.sh <role> install
```

Fix every `FAIL`. Install renders role-owned Compose/UI files and, on ROS hosts,
the Fast DDS peer profile derived from the manifest. Replaced files receive a
timestamped backup.

## 5. Start and verify in order

Start AI Max, Server PC, then TB3. After each start, require both status and
runtime preflight to pass.

```bash
bash deploy/role.sh <role> start
bash deploy/role.sh <role> status
bash deploy/preflight.sh <role> --phase runtime
```

Commands resolve `TB3_HOST_MANIFEST` first, then the standard user path, then
the legacy repository-local `host-manifest.toml`. Pass `--manifest PATH` when a
release intentionally lives elsewhere.

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
