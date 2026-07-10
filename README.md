# TurtleBot3 Multimodal Interaction

ROS 2 and deployment tooling for the three-host TurtleBot3 multimodal stack:

- TurtleBot3: base bringup, camera, microphone, face, speech, and motion.
- Server PC: ASR, TTS, dashboard, VLM client, validation, and behavior plans.
- AI Max: llama.cpp Qwen3-VL service and the inference dashboard.

The repository root is the ROS 2 package `tb3_multimodal_interaction`. Clone it
directly into `workspace/ros2_ws/src/tb3_multimodal_interaction` on the Server PC
and TurtleBot3. On AI Max it may be cloned anywhere under `/home/user/ROS_Cui`.

## Quick start

1. Copy `.env.example` to `.env` and review host paths.
2. Install role-specific runtime configuration:
   - Server PC: `bash deploy/server_pc/install.sh`
   - TurtleBot3: `bash deploy/tb3/install.sh`
3. Start roles in order:
   - AI Max: `bash deploy/ai_max/start.sh`
   - Server PC: `bash deploy/server_pc/start.sh`
   - TurtleBot3: `bash deploy/tb3/start.sh`
4. Verify from the TB3 checkout: `bash scripts/health_check_full.sh full` inside
   the `turtlebot3` container.

Real motion is disabled by default. Set `TB3_BEHAVIOR_DRY_RUN=false` only after
clearing the floor and confirming emergency-stop access.

See [deployment](docs/deployment.md), [migration map](docs/migration-map.md),
[inventory](docs/inventory.md), and [rollback](docs/rollback.md).
