# Fresh-host prerequisites

This is the inventory to complete before the first build. Copy
`.env.example` to `.env` on every host, change only that host's values, and run
the role preflight described in [preflight.md](preflight.md).

## Role manifest

| Role | Tested platform | Required software | External assets | Network | Hardware |
| --- | --- | --- | --- | --- | --- |
| AI Max | Ubuntu 24.04.4 LTS, x86_64; Docker 29.5.2; Compose 5.1.4 | Git, curl, iproute2, iputils-ping, Docker/Compose, a working llama.cpp build | llama.cpp checkout and `llama-server`; Qwen model GGUF; matching mmproj GGUF; VLM logs | Local address `AI_MAX_IP`; inbound TCP `VLM_PORT` and `VLM_DASHBOARD_PORT`; outbound HTTPS/SSH 443 for setup and updates | AMD/ATI display controller `1002:1586`; enough RAM and storage for the selected model |
| Server PC | Ubuntu 24.04.4 LTS, x86_64; Docker 29.6.0; Compose 5.2.0 | Git, curl, Python 3, iproute2, iputils-ping, Docker/Compose; ROBOTIS Jazzy base checkout | SenseVoiceSmall cache; ASR/TTS Docker layers; repository `.env`; deploy key | Local address `SERVER_PC_IP`; TCP `SERVER_DASHBOARD_PORT`; routes to AI Max and TB3; ROS 2 DDS traffic on the shared subnet/domain | No direct robot devices; sufficient disk/RAM for ASR and TTS images |
| TurtleBot3 | Ubuntu 24.04.4 LTS, aarch64; Docker 29.4.3; Compose 5.1.3 | Git, curl, iproute2, iputils-ping, Docker/Compose, `alsa-utils`, `x11-xserver-utils`, Openbox, Epiphany; ROBOTIS Jazzy base checkout | Repository `.env`; deploy key; local desktop/UI assets and device-specific settings | Local address `TB3_IP`; TCP `TB3_UI_PORT`; routes to Server PC and AI Max; ROS 2 DDS traffic on the shared subnet/domain | Burger base, OpenCR, LDS-02, `/dev/video0`, configured capture/playback ALSA cards, X display `:0`, speaker and touch display |

All three hosts require `NTPSynchronized=yes` before runtime work. The timezone
may differ; event ordering uses synchronized wall-clock timestamps and duration
measurements use monotonic clocks.

## Tested revisions and assets

Recorded on 2026-07-16 at the Week 7 P1 entry point.

| Component | Tested identity |
| --- | --- |
| Application repository | deployed baseline commit `09f67b30dcc9c2abef0860ddb600e9ade10a5b67` |
| ROBOTIS `turtlebot3` checkout | commit `da785b7201d317e6e2a662e41bb3d3fd50ebd503`, branch `main` |
| ROBOTIS Jazzy image | `robotis/turtlebot3:jazzy-latest`, image ID `sha256:c510fb503c71ef9bfbd8165e4e2bbcac8006d91c548aea246113c4fbe352ba4d` |
| llama.cpp | commit `32120c10e33baae8061e9961e6c3f1248302a331`, describe `b9664-4-g32120c10e`, llama-server build `9668` |
| Qwen3-VL 8B model | snapshot `f982a07559d4a2f6c8744d840bf6fccab30eea96`; `Qwen3VL-8B-Instruct-Q4_K_M.gguf`, 5,027,784,800 bytes, SHA-256 `67d1659bfe71b89d50b45a4ad1a9e5b997e5bb16ce5da66a6a6167abd569e9e2` |
| Qwen3-VL 8B projector | `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf`, 752,289,728 bytes, SHA-256 `c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd` |
| SenseVoiceSmall | `model.pt`, 936,291,369 bytes, SHA-256 `833ca2dcfdf8ec91bd4f31cfac36d6124e0c459074d5e909aec9cabe6204a3ea` |

The application commit is the clean deployed baseline. Week 7 changes must be
reviewed and committed before promoting them as a new deployment identity.

## Assets deliberately excluded from Git

| Asset | Expected location or owner | Recovery action |
| --- | --- | --- |
| Qwen GGUF and mmproj | AI Max paths in `VLM_MODEL_PATH` and `VLM_MMPROJ_PATH` | Download the matching snapshot, verify size and SHA-256, then update `.env` |
| llama.cpp source and binary | `LLAMA_CPP_DIR` and `LLAMA_SERVER` on AI Max | Check out the tested commit and rebuild for the host accelerator |
| SenseVoiceSmall | `SENSEVOICE_MODEL_DIR` on Server PC | Restore the complete model directory and verify `model.pt` before Compose build |
| Hugging Face/ModelScope/Kokoro/UniDic caches | Host caches or Docker image layers | Re-download or restore; never add caches to this repository |
| Credentials | Per-host private deploy key under `~/.ssh`; public half in GitHub Deploy Keys | Recreate a host-specific key; never copy a personal token or private key into Git |
| Host configuration | Ignored `.env` on each host | Start from `.env.example`, then verify all role-specific paths and addresses |
| Device-specific settings | TB3 ALSA names, device paths, display, Openbox/idesk files, local `~/tb3_ui` assets | Re-enumerate devices and rerun `deploy/tb3/install.sh` |
| Runtime output | model caches, VLM logs, ROS logs, recordings, backups, artifacts | Restore only if required for evidence; these paths are ignored by Git |

## Configuration map

| Concern | `.env` variables | Runtime consumer |
| --- | --- | --- |
| Host addresses | `AI_MAX_IP`, `SERVER_PC_IP`, `TB3_IP` | deploy scripts, dashboards, VLM client, preflight |
| Public service ports | `VLM_PORT`, `VLM_DASHBOARD_PORT`, `SERVER_DASHBOARD_PORT`, `TB3_UI_PORT` | role start scripts, ROS launches, dashboards, health checks |
| ROS discovery | `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE` | `scripts/ros_env.sh`; both ROS hosts must match |
| Motion safety | `TB3_BEHAVIOR_DRY_RUN`, `TB3_BEHAVIOR_MAX_DURATION` | behavior executor startup; dry-run remains the default |
| Existing workspaces | `SERVER_COMPOSE_DIR`, `TB3_COMPOSE_DIR`, `SERVER_REPO_DIR`, `TB3_REPO_DIR`, `ROS_CONTAINER` | install/start scripts and preflight |
| AI assets | `AI_MAX_ROOT`, `AI_MAX_REPO_DIR`, `LLAMA_CPP_DIR`, `LLAMA_SERVER`, `VLM_MODEL_PATH`, `VLM_MMPROJ_PATH` | AI Max startup and preflight |
| Server model | `SENSEVOICE_MODEL_DIR` | Server preflight and ASR image build context |
| TB3 devices | `TB3_CAMERA_DEVICE`, `TB3_OPENCR_DEVICE`, `TB3_LIDAR_DEVICE`, `TB3_MIC_ALSA_DEVICE`, `TB3_SPEAKER_ALSA_DEVICE`, `TB3_DISPLAY` | device launch, UI startup, preflight |
| Clock policy | `NTP_REQUIRED` | preflight |

## Hard-coded runtime audit

Configured now:

- llama.cpp, Qwen model and mmproj paths are explicit `.env` values passed
  through the AI Max restart chain.
- Server dashboard, TB3 UI, VLM and dashboard ports are explicit and passed to
  production launch/start paths.
- TB3 camera, microphone, speaker and display settings are explicit and passed
  into the ROS device launch.
- The stale VLM client fallback port `18081` was corrected to `18082`.

Documented limitations:

- `config/fastdds_initial_peers.xml` is a tracked static profile containing the
  current Server PC and TB3 addresses and Fast DDS participant ports
  `14910..14929`. Preflight fails when `.env` addresses no longer match it; the
  profile must then be updated and redeployed.
- `/workspace/ros2_ws`, the ROS container name, and the ROBOTIS Jazzy Compose
  layout form the current container contract. Changing that contract requires a
  coordinated Compose and script migration, not only an `.env` edit.
- Several Python nodes retain current-lab fallback addresses for direct manual
  launches. Production launch files and role start scripts override them from
  `.env`.
- The current routed topology permits Server PC to reach AI Max, but not AI Max
  to initiate a connection to the Server PC subnet. Server PC therefore pushes
  dashboard state to AI Max's `/api/server_status`; the AI dashboard's direct
  Server URL remains best-effort only.
- The TB3 desktop link assumes the `turtlebot3` account and local `~/tb3_ui`
  launcher assets. Its port is rendered from `.env` during install; changing the
  account or asset location requires updating the link template.

## Read-only GitHub deploy key over port 443

Create a different key on each runtime host:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/tb3_multimodal_deploy -C "$(hostname)-tb3-deploy"
chmod 600 ~/.ssh/tb3_multimodal_deploy
```

Add only the `.pub` value at repository **Settings → Deploy keys → Add deploy
key** and leave write access disabled. GitHub deploy keys are repository-scoped
and read-only by default: <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys>.

Configure this checkout without changing the user's global SSH settings:

```bash
git remote set-url origin git@github.com:r1file/tb3-multimodal-interaction.git
git config --local core.sshCommand \
  "ssh -i $HOME/.ssh/tb3_multimodal_deploy -o IdentitiesOnly=yes -o Hostname=ssh.github.com -p 443"
ssh -T -p 443 -i ~/.ssh/tb3_multimodal_deploy git@ssh.github.com
git fetch --prune origin
```

GitHub documents `ssh.github.com:443` as the HTTPS-port SSH endpoint:
<https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port>.
The successful SSH test intentionally reports that shell access is unavailable.
