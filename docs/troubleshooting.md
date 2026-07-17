# Failure triage

Start with the canonical status and the same manifest used to start the role:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> status --manifest PATH
```

The JSON `logs` object gives the actual manifest-derived paths; do not copy a
path from another machine.

| Symptom/state | First evidence | Next action |
| --- | --- | --- |
| Manifest validation fails | Read the exact repository/commit/path/placeholder/dirty-checkout error | Correct the external manifest or restore the exact clean release; never patch source on one host |
| AI `starting`/`unhealthy` | Status `llama_http`, `llama_server`, dashboard component and configured llama log directory | Check pinned model/mmproj assets and GPU allocation, then one canonical restart |
| Peer `unreachable`/`stale` | Endpoint URL, `relay_age_s`, host clocks and relay log from status | Repair route/NTP/relay before restarting unrelated services |
| Server node missing | Status component count and `server_stack`/`vlm_client` log paths | Run runtime preflight, then canonical Server restart |
| TB3 bringup missing | `tb3_bringup` log and runtime preflight device/odom results | Check manifest OpenCR/LiDAR mapping and base power |
| TB3 device/UI unhealthy | `device_stack` log, UI `/state.json`, `systemctl --user status tb3-ui-*` | Check manifest camera/audio/display values, then restart in dry-run |
| Duplicate process/node | Status component with `count > 1` | Use canonical restart; do not add an ad-hoc `ros2 run/launch` owner |
| Fast DDS mismatch | Runtime preflight profile diff | Rerun role install with the same manifest on both ROS hosts |
| Upgrade build references a removed file | Package build log | Canonical start clears only this package's generated build/install directories before rebuilding |

Logs, manifest runtime backups and pre-migration checkout backups are evidence;
do not delete them during triage.
