# Script Classification

The old stage-numbered files remain in host backups until the renamed stack is
accepted. The clean repository contains only the functional names below.

| Old script | New location | Class |
|---|---|---|
| `install_week2_audio_tools_container.sh` | Removed; image dependencies live in the pinned Dockerfile | Delete |
| `start_face_gui.sh` | `scripts/start_face_gui.sh` | Keep |
| `start_tb3_bringup.sh` | `scripts/start_tb3_bringup.sh` | Keep |
| `start_touch_gui_host.sh` | `scripts/start_touch_gui_host.sh` | Keep |
| `start_week2_executor.sh` | `scripts/start_device_stack.sh` | Keep / rename |
| `start_week2_gui_stack_host.sh` | `scripts/start_tb3_stack_host.sh` | Keep / rename |
| `start_week2_server_stack.sh` | `scripts/start_server_dashboard.sh` | Keep / rename |
| `start_week3_server_stack_host.sh` | `scripts/start_server_stack_host.sh` | Keep / rename |
| `start_week5_behavior_executor_host.sh` | `scripts/start_behavior_executor_host.sh` | Keep / rename |
| `start_week5_vlm_client_host.sh` | `scripts/start_vlm_client_host.sh` | Keep / rename |
| `wait_tb3_bringup_ready.sh` | `scripts/wait_tb3_bringup_ready.sh` | Keep |
| `week2_manual_test.sh` | `scripts/smoke_manual_io.sh` | Keep / rename |
| `week2_mic_test_host.sh` | `scripts/smoke_microphone_host.sh` | Keep / rename |
| `week2_ros_env.sh` | `scripts/ros_env.sh` | Keep / rename |
| `week5_behavior_dry_run_smoke.sh` | `scripts/smoke_behavior_executor_dry_run.sh` | Keep / rename |
| `week5_behavior_no_motion_hardware_smoke.sh` | `scripts/smoke_behavior_no_motion.sh` | Keep / rename |
| `week5_behavior_short_motion_hardware_smoke.sh` | `scripts/smoke_behavior_short_motion.sh` | Keep / rename |
| `week5_language_smoke.py` | `scripts/smoke_language_contract.py` | Keep / rename |
| `week5_stack_health_check.sh` | `scripts/health_check_full.sh` | Keep / rename |
| `week5_vlm_client_smoke.sh` | `scripts/smoke_vlm_client.sh` | Keep / rename |
| `week6_demo_expectation_check.py` | `tools/analysis/analyze_demo_expectations.py` | Keep as analysis tool |
| `week6_fallback_metrics.py` | `tools/analysis/analyze_fallback_metrics.py` | Keep as analysis tool |
| `week6_p5_asr_injected_runner.py` | `tools/analysis/run_asr_injected_scenarios.py` | Keep as analysis tool |

Delete candidates after acceptance: old host copies of renamed scripts,
`__pycache__`, `.pyc`, `.DS_Store`, stale PID files, and temporary logs.

## Current entrypoint policy

- `deploy/role.sh` is the only normal manifest initialization and
  install/start/stop/restart/status entry.
- `deploy/<role>/*.sh` and `scripts/start_*` are owned implementation helpers;
  do not mix them with the canonical role command during normal operation.
- `scripts/smoke_*`, `scripts/health_check_full.sh`, and
  `scripts/validate_repository.sh` are repeatable verification tools.
- `tools/analysis/` and the two legacy-data conversion scripts are offline
  analysis tools. They never start a role or overwrite raw evidence.
- Old stage-numbered runtime scripts are not shipped in the repository. Their
  names remain only in migration and rollback documentation.
