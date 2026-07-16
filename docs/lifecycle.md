# Role Lifecycle and Logs

## One interface

Run exactly one role-local command on each machine:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> <install|start|stop|restart|status>
```

Deployment order is AI Max, Server PC, TB3. Shutdown order is the reverse. A
`restart` is an owned `stop` followed by `start`; repeated starts also remove
matching role-owned processes before launching replacements. The TB3 behavior
executor defaults to `dry_run=true` even when the environment variable is absent.

`stop` deliberately retains Docker itself, models, workspaces, logs, state files,
and rollback backups. It stops only the selected role's containers and processes.

## Ownership

| Role | Owned runtime |
| --- | --- |
| AI Max | llama-server process and `tb3-ai-max-dashboard` container |
| Server PC | `turtlebot3`, `tb3_asr`, `tb3_tts`, dashboard/VLM ROS nodes, status relay |
| TB3 | `turtlebot3` ROS container, device/face/behavior nodes, Xorg/Openbox/iDesk/Epiphany UI units |

The Server-to-AI status relay is never started manually. Its PID, log, start,
health, and stop are controlled by the Server PC role scripts.

The AI Max host is not required to route directly to the Server PC subnet. AI
status uses the dashboard's fresh relay payload and reports its `source` and
`relay_age_s`. TB3 display processes run outside the SSH session as transient
systemd services (`tb3-ui-xorg`, `tb3-ui-openbox`, `tb3-ui-idesk`, and
`tb3-ui-browser`) so a cold start remains visible after logout.

## Persistent log locations

Defaults can be changed in `.env`:

| Role | Host directory | Key logs |
| --- | --- | --- |
| AI Max | `/home/user/ROS_Cui/runtime_logs/tb3_multimodal_interaction` | lifecycle state; llama logs remain in `/home/user/ROS_Cui/vlm_server_logs` |
| Server PC | `/home/user/ROS_Cui/turtlebot3/docker/jazzy/workspace/runtime_logs/tb3_multimodal_interaction` | `server_stack.log`, `vlm_client.log`, `server_status_relay.log` |
| TB3 | `/home/turtlebot3/turtlebot3/docker/jazzy/workspace/runtime_logs/tb3_multimodal_interaction` | `tb3_bringup.log`, `device_stack.log`, `behavior_executor.log`, UI logs |

The Server/TB3 container path is
`/workspace/runtime_logs/tb3_multimodal_interaction`, backed by the existing
host workspace mount. Before a component starts, its current log is renamed with
a timestamp. Files older than `RUNTIME_LOG_RETENTION_DAYS` (default 14), and
versions beyond `RUNTIME_LOG_RETAIN_FILES` (default 20), are removed. Backups are
outside this policy and are never removed by lifecycle scripts.

## Status contract

`status` emits JSON and exits 0 only when the local role and required upstream
dependencies are `ready`. Component states are:

- `starting`: within the configured startup grace period.
- `stale`: previously usable status is older than the freshness threshold.
- `missing`: expected process, ROS node, or container is absent.
- `unhealthy`: component exists or responds but violates its health contract,
  including duplicate critical nodes.
- `unreachable`: an HTTP/network endpoint cannot be contacted.
- `ready`: exactly one expected critical node/process is present and health passes.
- `stopped`: the role was intentionally stopped and owned runtime is absent.

Both dashboards expose the same diagnostic vocabulary in their status JSON.
ROS node checks use one graph snapshot per role. If the daemon snapshot is
incomplete immediately after a container restart, status performs one bounded
fresh-discovery retry before reporting a node missing.
