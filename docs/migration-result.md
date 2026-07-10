# P6 Migration Result

Migration date: 2026-07-10.

## Repository

- Private GitHub repository: `r1file/tb3-multimodal-interaction`.
- Initial baseline commit: `54e37a9`.
- All three runtime hosts use independent read-only deploy keys over GitHub SSH
  port 443.

## Validation

- Local shell syntax, Python compilation, Compose config, path-reference, large
  file, and credential-pattern checks passed.
- Behavior contract: 10/10 tests passed locally, on Server PC, and on TB3.
- Full TB3 health check: `TB3_STACK_HEALTH_PASS`.
- TB3 host startup now waits for the six device-stack nodes to appear in the
  ROS graph before running the full health check, avoiding cold-start discovery
  false negatives.
- Server services: `turtlebot3`, `tb3_asr`, `tb3_tts`, `server_ui`, `vlm`, and
  `behavior` all reported `ok`.
- VLM trace `server_ui_1783682398149`: accepted, no fallback, English response,
  Qwen3-VL-8B, 4947 ms total, behavior `finished`.
- English TTS fresh image: `af_heart`, `state=done`, 2.425 s audio, TB3 speech
  playback `done`.
- AI Max dashboard: llama health true, model endpoint 18082, Server PC status
  received through relay.

## Runtime safety state

The migrated behavior executor is intentionally left at `dry_run=true`. Enable
real motion only after a physical floor and emergency-stop check.

## Retention

The old package directories and timestamped backups remain in place. Do not
delete them until a user-run real-motion demo and a later rollback-retention
review are complete.
