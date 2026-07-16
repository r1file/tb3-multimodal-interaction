# Failure Triage

Start every investigation with the role-local status command:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> status
```

| Symptom/state | First log or health command | Likely next action |
| --- | --- | --- |
| AI `starting` for more than 180 s | `tail -n 100 /home/user/ROS_Cui/vlm_server_logs/*.log` | Check model/mmproj paths and GPU allocation, then restart AI Max. |
| AI `unhealthy` | `curl -v http://127.0.0.1:18082/health` and `docker logs tb3-ai-max-dashboard` | Inspect HTTP status/model load; do not start a second server manually. |
| AI/Server `unreachable` | `curl -v http://ROLE_IP:PORT/status.json`; inspect AI `server_pc.source` and `relay_age_s` | Check the Server relay log before assuming AI Max needs a direct route to the Server subnet. |
| Server `missing` dashboard/VLM node | `tail -n 100 /home/user/ROS_Cui/turtlebot3/docker/jazzy/workspace/runtime_logs/tb3_multimodal_interaction/{server_stack,vlm_client}.log` | Run Server status, then one canonical Server restart. |
| Server relay missing/stale | `tail -n 100 .../runtime_logs/tb3_multimodal_interaction/server_status_relay.log` | Restart the Server role; never launch the relay separately. |
| TB3 bringup missing | `tail -n 100 /home/turtlebot3/turtlebot3/docker/jazzy/workspace/runtime_logs/tb3_multimodal_interaction/tb3_bringup.log`; run `scripts/check_tb3_bringup_graph.py 6` inside the ROS container | Check OpenCR/lidar mappings and distinguish hardware startup from delayed ROS graph discovery. |
| TB3 device/UI unhealthy | Inspect `device_stack.log`, `curl -v http://127.0.0.1:8765/state.json`, and `systemctl --user status tb3-ui-{openbox,browser}.service` | Check camera/audio/display resources, then restart TB3 in dry-run. |
| Duplicate node/process (`count > 1`) | Inspect the `components` array from status; `ros2 node list` inside the role container | Use canonical `restart`; do not use ad-hoc `ros2 run/launch`. |
| `stale` dashboard data | Compare payload `time`, `relay_age_s`, and host clocks | Check NTP and relay reachability before restarting services. |

The abbreviated `.../runtime_logs` Server/TB3 paths above expand to the full host
directories listed in [lifecycle.md](lifecycle.md). Logs and retained backups are
diagnostic evidence; do not delete them during triage.
