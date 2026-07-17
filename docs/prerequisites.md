# Fresh-host prerequisites

Prepare all three hosts before creating the release manifest.

| Role | Tested platform | Required software/assets | Hardware/network |
| --- | --- | --- | --- |
| AI Max | Ubuntu 24.04 x86_64 | Git, curl, Docker/Compose, llama.cpp `llama-server`, Qwen GGUF and matching mmproj | supported accelerator, model RAM/storage, VLM and dashboard ports |
| Server PC | Ubuntu 24.04 x86_64 | Git, curl, Python 3, Docker/Compose, ROBOTIS Jazzy checkout, SenseVoiceSmall | routes to AI Max/TB3, dashboard port, sufficient ASR/TTS disk/RAM |
| TB3 | Ubuntu 24.04 aarch64 | Git, curl, Docker/Compose, ROBOTIS Jazzy checkout, ALSA tools, Xorg/Openbox/iDesk/Epiphany | Burger/OpenCR/LDS-02, camera, microphone, speaker, display, routes to peers |

All hosts need `iproute2`, `iputils-ping`, a local address matching the manifest
and `NTPSynchronized=yes` when `[runtime].ntp_required=true`.

## Tested external assets

| Component | Tested identity |
| --- | --- |
| ROBOTIS `turtlebot3` | commit `da785b7201d317e6e2a662e41bb3d3fd50ebd503` |
| llama.cpp | commit `32120c10e33baae8061e9961e6c3f1248302a331`, build 9668 |
| Qwen3-VL 8B model | 5,027,784,800 bytes; SHA-256 `67d1659bfe71b89d50b45a4ad1a9e5b997e5bb16ce5da66a6a6167abd569e9e2` |
| matching mmproj | 752,289,728 bytes; SHA-256 `c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd` |
| SenseVoiceSmall `model.pt` | 936,291,369 bytes; SHA-256 `833ca2dcfdf8ec91bd4f31cfac36d6124e0c459074d5e909aec9cabe6204a3ea` |

Models, caches, credentials, logs and backups are never release-artifact files.
Their absolute locations are declared in the manifest and verified by
preflight.

## Configuration ownership

`config/host-manifest.example.toml` is the schema example. A populated manifest
is external and copied unchanged to all hosts. It owns:

- release repository/commit and all role checkout/workspace paths;
- addresses, ports, ROS domain and generated Fast DDS peers;
- container/image identities and external model paths;
- TB3 devices, audio, display, velocity-topic candidates and motion safety;
- lifecycle log roots, retention, startup grace and NTP policy.

Runtime launchers reject a missing, partial, wrong-repository, wrong-checkout or
wrong-commit manifest. Fixed `/workspace/...` values are the container artifact
layout; ROS topic names and JSON schemas are application interfaces, not host
configuration.

## Read-only GitHub deploy key over port 443

Create a separate repository-scoped key on each runtime host and add only its
public half as a read-only GitHub Deploy Key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/tb3_multimodal_deploy -C "$(hostname)-tb3-deploy"
chmod 600 ~/.ssh/tb3_multimodal_deploy
git config --local core.sshCommand \
  "ssh -i $HOME/.ssh/tb3_multimodal_deploy -o IdentitiesOnly=yes -o Hostname=ssh.github.com -p 443"
ssh -T -p 443 -i ~/.ssh/tb3_multimodal_deploy git@ssh.github.com
git fetch --prune origin
```

Never copy a personal token or private key into the repository or manifest.
