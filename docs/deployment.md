# Three-Host Deployment

## Checkout paths

- Server PC:
  `/home/user/ROS_Cui/turtlebot3/docker/jazzy/workspace/ros2_ws/src/tb3_multimodal_interaction`
- TurtleBot3:
  `/home/turtlebot3/turtlebot3/docker/jazzy/workspace/ros2_ws/src/tb3_multimodal_interaction`
- AI Max: `/home/user/ROS_Cui/tb3-multimodal-interaction`

Copy `.env.example` to `.env` on each host and keep `.env` out of Git.

## First migration

Server PC:

```bash
bash deploy/server_pc/install.sh
bash deploy/server_pc/start.sh
```

TurtleBot3:

```bash
bash deploy/tb3/install.sh
bash deploy/tb3/start.sh
```

AI Max:

```bash
bash deploy/ai_max/start.sh
```

Start order is AI Max, Server PC, then TurtleBot3. Real motion remains disabled
until `TB3_BEHAVIOR_DRY_RUN=false` is set explicitly.

## Routine update

```bash
git pull --ff-only
```

Then rerun only the local role start script. Each ROS role rebuilds the package
inside the existing `turtlebot3` container before starting nodes.

## Verification

- AI Max VLM: `http://192.168.64.246:18082/health`
- AI Max dashboard: `http://192.168.64.246:18181/`
- Server dashboard: `http://192.168.250.30:8775/`
- TB3 UI: `http://192.168.250.10:8765/`
- Full health: `bash scripts/health_check_full.sh full` inside the TB3 container.
