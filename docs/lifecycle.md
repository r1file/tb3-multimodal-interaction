# Role lifecycle and logs

Use one role-local interface with the same manifest for every action:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> \
  <install|start|stop|restart|status> --manifest PATH
```

Start order is AI Max → Server PC → TB3; shutdown is the reverse. Repeated
starts first remove matching role-owned runtime. Stop preserves models,
workspaces, logs, state and backups.

| Role | Owned runtime |
| --- | --- |
| AI Max | configured llama-server process and dashboard container |
| Server PC | configured ROS, ASR and TTS containers; dashboard/VLM nodes; status relay |
| TB3 | configured ROS container; device/face/behavior nodes; Xorg/Openbox/iDesk/Epiphany services |

Log roots, retention and startup grace come from `[runtime]` and each role's
`runtime_log_dir`. Server/TB3 container logs use the workspace-relative path
exported as `CONTAINER_RUNTIME_LOG_DIR`.

`status` returns JSON and exits zero only when the local role and required
upstream components are ready. It includes the manifest ID, SHA-256 and release
commit so three hosts can prove they run one deployment.

States are `starting`, `stale`, `missing`, `unhealthy`, `unreachable`, `ready`
and `stopped`. Critical duplicate processes/nodes are unhealthy. ROS checks use
one graph snapshot plus one bounded fresh-discovery retry.

Server PC startup does not report ready while speech models are still loading.
The ASR container preloads the single multilingual SenseVoiceSmall model. The
TTS container constructs and warms the existing Japanese, Chinese and English
Kokoro pipelines and voices. Each container writes a private readiness marker,
and the canonical Server PC launcher waits for both markers within the manifest
startup grace period. Language selection continues through the existing adapter;
no additional routing service is introduced.
