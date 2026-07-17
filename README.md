# TurtleBot3 Multimodal Interaction

ROS 2 and deployment tooling for the three-host TurtleBot3 multimodal stack:

- TurtleBot3: base bringup, camera, microphone, face, speech, and motion.
- Server PC: ASR, TTS, dashboard, VLM client, validation, and behavior plans.
- AI Max: llama.cpp Qwen3-VL service and the inference dashboard.

The repository root is the ROS 2 package `tb3_multimodal_interaction`. Clone it
directly into `workspace/ros2_ws/src/tb3_multimodal_interaction` on the Server PC
and TurtleBot3. On AI Max it may be cloned anywhere under `/home/user/ROS_Cui`.

The Week7 platform baseline is engineering-complete: lifecycle, diagnostics,
evaluation logging, dashboards, safety boundaries, automated regressions, and a
targeted post-deployment physical I/O smoke are verified. The formal
presentation and any release tag remain separate operator/publication events.
Real motion is disabled by default.

## Quick start

1. Follow the [fresh-host reproduction guide](docs/reproduction.md), including
   prerequisites and external model assets.
2. Copy `.env.example` to `.env` and review every role-specific path and address.
3. Run `bash deploy/preflight.sh <role> --phase install` and fix every failure.
4. Install role-specific runtime configuration with
   `bash deploy/role.sh <role> install`.
5. Start roles in order:
   - AI Max: `bash deploy/role.sh ai_max start`
   - Server PC: `bash deploy/role.sh server_pc start`
   - TurtleBot3: `bash deploy/role.sh tb3 start`
6. After each start, run the matching `--phase runtime` preflight. Verify the
   full stack from TB3 with `bash scripts/health_check_full.sh full` inside the
   `turtlebot3` container.

To start only the TB3 display path (`face_display_node` on port 8765, Xorg,
Openbox, and Epiphany) without the remaining device or behavior nodes, run on
the TB3 host:

```bash
bash scripts/start_tb3_display_only_host.sh
```

Before publishing a change, run `bash scripts/validate_repository.sh`. In a ROS
Jazzy environment this executes the complete test suite; outside ROS it runs
the repository-safe subset plus syntax, asset, size, and credential checks.

The frozen P4 scenario matrix and operator gates are documented in the
[official demo runbook](docs/demo-runbook.md).

Real motion is disabled by default. Set `TB3_BEHAVIOR_DRY_RUN=false` only after
clearing the floor and confirming emergency-stop access. See the
[hardware contract](docs/hardware.md) and [known limitations](docs/limitations.md).

The [documentation index](docs/README.md) separates current operator material,
research/evaluation evidence, and historical migration records. Release gates
are tracked in the [Week8 release checklist](docs/release-checklist.md).
