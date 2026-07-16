# Week 7 P2 Lifecycle and Diagnostics Evidence

Date: 2026-07-16 JST

## Scope

- Canonical command: `bash deploy/role.sh <role> <install|start|stop|restart|status>`
- Deployment order: AI Max, Server PC, TB3
- TB3 safety policy: `TB3_BEHAVIOR_DRY_RUN=true`; no real-motion test in P2

## Pre-change baseline

- AI Max: one healthy llama-server and one dashboard container.
- Server PC: ROS stack healthy, but two status relay processes were present
  (`/tmp/server_status_relay.py` plus the repository relay). This is the duplicate
  lifecycle defect P2 is intended to remove.
- TB3: bringup/device/behavior components running; behavior executor command line
  showed `dry_run:=true`.

## Implementation evidence

- Role-owned stop scripts retain Docker daemons, models, workspaces, persistent
  logs, and all backup directories.
- Server relay PID/log moved from `/tmp` into the Server persistent runtime log
  directory and is started/stopped only by the Server role.
- Server/TB3 operational logs moved to the existing persistent `/workspace` bind
  mount. Rotation defaults: 14 days and 20 retained versions.
- Role status JSON distinguishes `starting`, `stale`, `missing`, `unhealthy`,
  `unreachable`, `ready`, and intentional `stopped`.
- AI and Server dashboard status payloads document and emit the same diagnostic
  vocabulary.
- AI start now waits for the dashboard API, and AI status accepts a fresh
  Server-to-AI relay payload instead of requiring an impossible direct route.
- Role status takes one ROS graph snapshot per role and retries with fresh
  discovery only when expected nodes are absent.
- TB3 bringup readiness uses one rclpy graph probe for both `/cmd_vel` and
  `/odom`, avoiding duplicate ROS CLI startup on the resource-constrained host.
- TB3 Xorg, Openbox, iDesk, and Epiphany are managed as transient systemd units;
  cold startup waits for the X display and a live WebKit page before succeeding.

## Local checks

- Bash syntax: passed for dispatcher, lifecycle, all role scripts, and modified
  start helpers.
- Python byte compilation: passed for status, process cleanup, AI dashboard, and
  Server dashboard modules.
- `git diff --check`: passed.
- Runtime log rotation smoke: passed; current log plus timestamped retained logs.
- `test_role_status_contract.py`: 6/6 passed.
- Full pytest run in the Server PC Jazzy container: 19/19 passed.

## Rollback verification

- Mac backup root present:
  `/Users/cuibaitao/Documents/Research_backups/p6_20260710_1935JST`
- Size: 46 MiB.
- All four retained `.tar.gz` archives passed read-only `tar -tzf` listing.
- AI Max backup root: 36 KiB, one archive, `tar -tzf` failures: 0.
- Server PC backup root: 200 KiB, one archive, `tar -tzf` failures: 0.
- TB3 backup root: 168 KiB, one archive, `tar -tzf` failures: 0.
- No archive was extracted, moved, or deleted.

## Restart acceptance table

| Cycle | AI Max | Server PC | TB3 | Critical duplicate count | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | ready in 7 s; llama/dashboard count 1 | ready in 31 s; relay/server_control/VLM client count 1 | ready in 108 s; bringup/device/behavior count 1 | 0 | pass |
| 2 | ready in 7 s; llama/dashboard count 1 | ready in 30 s; relay/server_control/VLM client count 1 | ready in 110 s; bringup/device/behavior count 1 | 0 | pass |

Both TB3 cycles used `dry_run=true`. No movement command was sent.

## Diagnostic acceptance table

| Role | Canonical status | Persistent log path verified | Failure can be triaged | Result |
| --- | --- | --- | --- | --- |
| AI Max | `overall_state=ready`; llama process and dashboard container count 1 | lifecycle state plus retained llama/restart logs | observed dashboard `unreachable` was isolated to API readiness/direct-route assumptions and fixed | pass |
| Server PC | `overall_state=ready`; required containers/nodes and relay count 1 | current plus two rotated server, VLM client, and relay logs | initial relay count 2 and missing node states were reported as `unhealthy`/`missing` and repaired by canonical restart | pass |
| TB3 | `overall_state=ready`; bringup/device/behavior count 1; four UI units active | current and rotated bringup/device/behavior logs plus UI logs | permission, no-TTY sudo, cold-display, and graph-discovery failures all identified their state/log before repair | pass |

## Acceptance conclusion

- The complete system was restarted twice in deployment order without duplicate
  critical nodes, relays, dashboard containers, or model servers.
- Every role exposes a canonical status command and verified persistent log path;
  real P2 failures were classified and repaired from those diagnostics.
- P2 implementation and both acceptance criteria are complete.
