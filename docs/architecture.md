# Architecture

## TurtleBot3 role

- `turtlebot3_bringup`: base, odometry, and velocity control.
- `device_stack.launch.py`: camera, microphone, face, speech, expression, and
  motion nodes.
- `behavior_executor_node`: validated plan execution with a final stop and
  optional dry-run.
- Touch UI on port 8765.

## Server PC role

- ASR and TTS adapters in dedicated Docker containers.
- `server_control_node` dashboard on port 8775.
- `vlm_behavior_client_node`: context selection, AI Max request, policy guards,
  validation, and behavior-plan publication.
- Status relay from Server PC to AI Max dashboard.

## AI Max role

- Existing llama.cpp runtime with Qwen3-VL GGUF and mmproj files.
- Default Qwen3-VL-8B service on port 18082.
- Read-only operations dashboard on port 18181.

## Stable interfaces

The migration changes package, file, service, and deployment names. ROS topic
contracts remain stable, including `/robot_ai/status`, `/robot_behavior/plan`,
`/robot_tts/request`, `/robot_face/expression`, and
`/robot_motion/action_cmd`. The VLM never publishes `/cmd_vel` directly.
