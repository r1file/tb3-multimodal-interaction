# Deployment preflight

The preflight is read-only. It does not install packages, pull images, restart
containers, move the robot, or modify devices.

Run it from the role's configured repository checkout:

```bash
cp .env.example .env
# Review every value in .env before continuing.
bash deploy/preflight.sh ai_max --phase install
bash deploy/preflight.sh server_pc --phase install
bash deploy/preflight.sh tb3 --phase install
```

Run only the command matching the current host. `install` verifies:

- Ubuntu, Git, Docker/Compose and required host commands;
- the configured local address, peer reachability, NTP synchronization and
  valid ports;
- the expected repository and ROBOTIS Compose layout;
- llama.cpp/Qwen assets on AI Max or SenseVoiceSmall on Server PC;
- camera, OpenCR, LiDAR, microphone, speaker and X display on TB3;
- that a listening application port belongs to the expected healthy service,
  or that the port is available before startup;
- that configured ROS peer addresses still match the tracked Fast DDS profile.

After starting a role in deployment order, run its runtime phase:

```bash
bash deploy/preflight.sh ai_max --phase runtime
bash deploy/preflight.sh server_pc --phase runtime
bash deploy/preflight.sh tb3 --phase runtime
```

The runtime phase additionally requires local HTTP health, upstream services in
the deployment order, ROS node/topic discovery, and a live TB3 `/odom` sample.
A successful run ends with `PREFLIGHT_PASS`. A failure ends with
`PREFLIGHT_FAIL`, returns a non-zero status, and prints a repair action beside
every failed condition.

## Clean-checkout rehearsal

Use a new directory and do not symlink or copy an old ROS package:

```bash
rehearsal_root="$(mktemp -d /tmp/tb3-clean-checkout.XXXXXX)"
git clone git@github.com:r1file/tb3-multimodal-interaction.git "$rehearsal_root/repo"
cd "$rehearsal_root/repo"
cp .env.example .env
```

On Server PC or TB3, set the matching `*_REPO_DIR` in `.env` to the new clone,
place the clone directly in a fresh `workspace/ros2_ws/src` when rehearsing an
actual build, and run `deploy/preflight.sh <role> --phase install`. Confirm:

```bash
git status --short
git rev-parse HEAD
test ! -e ../tb3_week2_executor
bash -n deploy/preflight.sh deploy/*/*.sh scripts/*.sh
python3 -m compileall -q tb3_multimodal_interaction launch
```

Delete the temporary directory after recording the commit, preflight result and
build/test result. A local source copy, ROS `build/`, `install/`, or old package
directory does not count as a clean checkout.
