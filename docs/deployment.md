# Three-Host Deployment

This page is the concise operator reference. For a machine with no prior
checkout, follow [reproduction.md](reproduction.md) from start to finish.

## Checkout paths

- Server PC:
  `/home/user/ROS_Cui/turtlebot3/docker/jazzy/workspace/ros2_ws/src/tb3_multimodal_interaction`
- TurtleBot3:
  `/home/turtlebot3/turtlebot3/docker/jazzy/workspace/ros2_ws/src/tb3_multimodal_interaction`
- AI Max: `/home/user/ROS_Cui/tb3-multimodal-interaction`

Copy `.env.example` to `.env` on each host and keep `.env` out of Git.
Review the complete dependency inventory in
[prerequisites.md](prerequisites.md), then run the matching install preflight:

```bash
bash deploy/preflight.sh ai_max --phase install
bash deploy/preflight.sh server_pc --phase install
bash deploy/preflight.sh tb3 --phase install
```

Only run the command for the current host. Fix every `FAIL` before building.

## Canonical lifecycle command

Every host uses the same entry point; only `<role>` changes:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> <install|start|stop|restart|status>
```

Do not mix this with direct component launch commands during normal operation.
The dispatcher is the canonical interface and the role scripts own all of their
processes, containers, PID files, state markers, and logs.

## First migration

Server PC:

```bash
bash deploy/role.sh server_pc install
bash deploy/role.sh server_pc start
```

TurtleBot3:

```bash
bash deploy/role.sh tb3 install
bash deploy/role.sh tb3 start
```

AI Max:

```bash
bash deploy/role.sh ai_max install
bash deploy/role.sh ai_max start
```

Start order is AI Max, Server PC, then TurtleBot3. Real motion remains disabled
until `TB3_BEHAVIOR_DRY_RUN=false` is set explicitly.

After each role starts, run its `--phase runtime` preflight before proceeding to
the next role. See [preflight.md](preflight.md) for the complete contract.

## Routine update

```bash
git status --short
git pull --ff-only
bash scripts/validate_repository.sh
```

Do not pull over host-edited source. Machine-specific values belong only in the
ignored `.env`. Then run `bash deploy/role.sh <role> restart` on the local role.
Each ROS role rebuilds the package inside the existing `turtlebot3` container
before starting nodes.

See [lifecycle.md](lifecycle.md) for ownership, persistent log paths, retention,
and idempotence rules. Use [troubleshooting.md](troubleshooting.md) when status
is not `ready`.

## Verification

- AI Max VLM: `http://$AI_MAX_IP:$VLM_PORT/health`
- AI Max dashboard: `http://$AI_MAX_IP:$VLM_DASHBOARD_PORT/`
- Server dashboard: `http://$SERVER_PC_IP:$SERVER_DASHBOARD_PORT/`
- TB3 UI: `http://$TB3_IP:$TB3_UI_PORT/`
- Full health: `bash scripts/health_check_full.sh full` inside the TB3 container.
- Role-local diagnostics: `bash deploy/role.sh <role> status`.

## Stop and rollback

Stop in reverse order: TB3, Server PC, AI Max.

```bash
bash deploy/role.sh tb3 stop
bash deploy/role.sh server_pc stop
bash deploy/role.sh ai_max stop
```

Stops preserve models, logs, state files, workspaces, and backups. If a verified
commit cannot be restarted, use the manual, read-before-write process in
[rollback.md](rollback.md); never extract a backup over a running role.
