# Week 7 P1 fresh-host and preflight evidence

Date: 2026-07-16 (Asia/Tokyo)

## Scope

P1 establishes a reproducible prerequisite inventory, explicit host
configuration, actionable preflight failures, and a clean-checkout rehearsal
for the three-host deployment.

## Artifacts

- `docs/prerequisites.md`: per-role OS, Docker/Compose, ROBOTIS base, host
  packages, external assets, network and hardware manifest.
- `.env.example`: addresses, ports, workspaces, model paths, ROS domain,
  behavior safety values, TB3 devices/display and NTP policy.
- `deploy/preflight.sh`: `ai_max`, `server_pc`, and `tb3` install/runtime gates.
- `docs/preflight.md`: operator procedure and clean-checkout rehearsal.
- `docs/github-workflow.md`: link to read-only deploy-key setup over
  `ssh.github.com:443`.

## Tested identities

The deployed baseline was application commit
`09f67b30dcc9c2abef0860ddb600e9ade10a5b67`. P1 was tested through temporary,
local-only rehearsal commits; neither was written to the canonical branch:

- `3d90fab43d2485664aba4445cdec516486540f6b`: isolated Server PC build/test.
- `e49f38a6783742abe93012e1c89c5802a7ec7d18`: final TB3 runtime preflight.

The only changes between those two snapshots were `deploy/preflight.sh` and
`docs/preflight.md`; ROS package source and tests were identical.

Exact ROBOTIS, llama.cpp and model identities, sizes and SHA-256 values are in
`docs/prerequisites.md`.

## Three-host preflight results

### AI Max

- Install: `PREFLIGHT_PASS role=ai_max phase=install warnings=0`.
- Runtime: `PREFLIGHT_PASS role=ai_max phase=runtime warnings=0`.
- Confirmed Ubuntu 24.04.4, Docker/Compose, NTP synchronization, llama.cpp
  binary, Qwen model/mmproj, VLM health on `18082`, and dashboard on `18181`.
- The topology audit confirmed that Server PC pushes dashboard status to AI
  Max; AI Max does not require a reverse route into the Server PC subnet.

### Server PC

- Clean install: `PREFLIGHT_PASS role=server_pc phase=install warnings=0`.
- Clean runtime: `PREFLIGHT_PASS role=server_pc phase=runtime warnings=0`.
- Confirmed SenseVoiceSmall, all three Compose services, AI Max/TB3 routes,
  dashboard health, AI Max VLM health, ROS nodes and the required ROS topics.

### TurtleBot3

- Clean install: `PREFLIGHT_PASS role=tb3 phase=install warnings=0`.
- Final clean runtime:
  `PREFLIGHT_PASS role=tb3 phase=runtime warnings=0`.
- NTP was synchronized with a measured offset of `-23.305 ms` during the final
  run.
- Confirmed camera, OpenCR, LiDAR, capture/playback ALSA cards, X display,
  Server/AI health, seven required ROS nodes, six required ROS topics and a
  live `/odom` sample.
- No real-motion command was issued; behavior execution remained dry-run.

## Clean-checkout rehearsal

The working tree was materialized as a temporary Git commit and bundle, then
cloned into new directories. This avoided copying or sourcing any legacy ROS
package directory.

Server PC rehearsal workspace:

`/home/user/ROS_Cui/turtlebot3/docker/jazzy/workspace/week7_p1_clean_ws`

- The `src` directory contained only the fresh
  `tb3_multimodal_interaction` clone.
- `git status --short` was empty before build.
- `test ! -e src/tb3_week2_executor` passed.
- `colcon build --packages-select tb3_multimodal_interaction
  --symlink-install` passed.
- `colcon test` result: `13 tests, 0 errors, 0 failures, 0 skipped`.

TB3 final rehearsal checkout:

`/tmp/week7_p1_clean_tb3/repo`

- Git identity was the final rehearsal snapshot `e49f38a...`.
- The checkout was clean and had no legacy sibling package.
- Runtime preflight passed with live `/odom`.

All temporary bundles, checkouts, probe directories and generated Python
caches were removed after evidence capture. Operational logs and the running
stack were not deleted or restarted.

## Acceptance

- A new operator can identify every non-Git dependency before building:
  **PASS**.
- Missing models, devices, network routes, invalid/occupied ports, unsynced
  clocks, Fast DDS mismatches and missing ROS endpoints produce actionable
  failures: **PASS**.
- A clean checkout builds and tests without an old ROS package directory:
  **PASS**.
