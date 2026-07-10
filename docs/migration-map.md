# Migration Map

## Packages and directories

| Old | New |
|---|---|
| `tb3_week2_executor` | `tb3_multimodal_interaction` |
| Python module `tb3_week2_executor` | `tb3_multimodal_interaction` |
| `week5_ai_max` | `ai_max_vlm_server` |
| `week3_model_cache` | `model_cache` |

## Launch files

| Old | New |
|---|---|
| `week2_executor.launch.py` | `device_stack.launch.py` |
| `week2_server.launch.py` | `server_dashboard.launch.py` |
| `week3_asr_adapter.launch.py` | `asr_adapter.launch.py` |
| `week3_tts_adapter.launch.py` | `tts_adapter.launch.py` |
| `week5_behavior_executor.launch.py` | `behavior_executor.launch.py` |
| `week5_vlm_behavior_client.launch.py` | `vlm_behavior_client.launch.py` |

## Main scripts

| Old | New |
|---|---|
| `start_week2_gui_stack_host.sh` | `start_tb3_stack_host.sh` |
| `start_week3_server_stack_host.sh` | `start_server_stack_host.sh` |
| `start_week5_vlm_client_host.sh` | `start_vlm_client_host.sh` |
| `start_week5_behavior_executor_host.sh` | `start_behavior_executor_host.sh` |
| `week5_stack_health_check.sh` | `health_check_full.sh` |
| `week5_vlm_client_smoke.sh` | `smoke_vlm_client.sh` |
| `week5_behavior_dry_run_smoke.sh` | `smoke_behavior_executor_dry_run.sh` |

Historical reports keep their original names. They are evidence, not runtime
entrypoints.
