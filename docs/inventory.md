# P6 Workspace Inventory

Inventory date: 2026-07-10.

## Local Mac

- Source workspace: `/Users/cuibaitao/Documents/Research` (122 MB).
- Canonical merge sources: `tb3_week2_executor` and `week5_ai_max`.
- Historical logs: `week6_logs` (excluded from Git except small summarized evidence).
- Original Git repository had no commits and treated the whole research workspace
  as untracked. This clean repository is intentionally separate.

## Server PC

- Host: `user@192.168.250.30`.
- Runtime root: `/home/user/ROS_Cui/turtlebot3/docker/jazzy` (947 MB).
- ROS source: `workspace/ros2_ws/src/tb3_week2_executor`.
- Host configuration: `docker-compose.yml`, `container.sh`, ASR/TTS/AV Dockerfiles.
- Runtime containers at inventory: `turtlebot3`, `week3_asr`, `week3_tts`.
- Server-side VLM, TTS, ASR, and dashboard sources matched the local canonical
  versions.

## TurtleBot3

- Host: `turtlebot3@192.168.250.10`.
- Runtime root: `/home/turtlebot3/turtlebot3/docker/jazzy` (119 MB).
- ROS source: `workspace/ros2_ws/src/tb3_week2_executor`.
- Device-specific assets: `~/.idesktop/tb3-web-ui.lnk` and Openbox autostart.
- Device/UI startup scripts matched the local canonical versions.
- Several server-only Python modules were older than Server PC and are no longer
  treated as host-specific source forks.

## AI Max

- Host: `user@192.168.64.246`.
- Root: `/home/user/ROS_Cui` (69 GB, mostly llama.cpp, models, and logs).
- Custom tools: `/home/user/ROS_Cui/week5_ai_max`.
- External dependency: `/home/user/ROS_Cui/llama.cpp`.
- Model caches: Qwen3-VL 2B, 8B, and 32B under Hugging Face cache.
- Custom AI Max tools matched local copies exactly.
- Unrelated containers are outside this repository and must not be modified.

## Backup set

All archives are mirrored under
`/Users/cuibaitao/Documents/Research_backups/p6_20260710_1935JST` and were
SHA-256 checked and extract-tested.
