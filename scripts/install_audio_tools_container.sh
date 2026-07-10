#!/usr/bin/env bash
set -euo pipefail

if ! docker ps --format '{{.Names}}' | grep -qx turtlebot3; then
  echo "Error: turtlebot3 container is not running." >&2
  echo "Start it first: cd ~/turtlebot3/docker/jazzy && ./container.sh start" >&2
  exit 1
fi

docker exec turtlebot3 bash -lc '
  set -e
  if command -v aplay >/dev/null 2>&1 &&
     command -v arecord >/dev/null 2>&1 &&
     command -v speaker-test >/dev/null 2>&1 &&
     command -v ffmpeg >/dev/null 2>&1 &&
     command -v v4l2-ctl >/dev/null 2>&1; then
    echo "TB3 audio/video tools already available in container."
    exit 0
  fi
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y alsa-utils file ffmpeg v4l-utils
'
