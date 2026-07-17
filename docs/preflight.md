# Deployment preflight

Preflight is read-only: it does not install, restart, move the robot or modify
devices.

```bash
python3 deploy/host_manifest.py validate --manifest PATH
bash deploy/preflight.sh <ai_max|server_pc|tb3> \
  --phase install --manifest PATH
```

When the manifest is installed at `~/.config/tb3/host-manifest.toml`, the
`--manifest` option may be omitted. Create the initial template with
`bash deploy/role.sh manifest-init`; complete it once and distribute the same
file to all three hosts.

The install phase verifies the complete manifest, release checkout identity,
local IP, routes, ports, NTP, Docker/Compose, external models and role-specific
hardware. On ROS roles it also proves that Fast DDS XML is derivable from the
manifest. Fix every `FAIL` before install.

After starting the role:

```bash
bash deploy/preflight.sh <role> --phase runtime --manifest PATH
```

Runtime additionally checks service HTTP health, installed Fast DDS content,
containers, upstream reachability, ROS nodes/topics and live TB3 odometry. A
successful run ends with `PREFLIGHT_PASS`; failures return non-zero with a
repair hint.

## Clean-checkout rehearsal

Clone into fresh paths declared in a temporary manifest, pin its exact commit,
and run repository validation plus install preflight. A copied package tree,
ROS `build/`/`install/`, or legacy package directory does not count as a clean
checkout.
