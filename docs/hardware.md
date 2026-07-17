# Hardware and device contract

Hardware names are manifest data, not portable source constants. Enumerate a
new TB3 host and set `[tb3]` before install.

## Base and LiDAR

Set `opencr_device`, `lidar_device`, `turtlebot3_model` and `lidar_model` to the
detected hardware. The base must publish `/odom` and subscribe to exactly one
resolved velocity topic. `cmd_vel_topic="auto"` searches only the explicit
`cmd_vel_candidates`; failure to find a subscriber stops startup.

## Camera and audio

Set `camera_device`, `mic_alsa_device` and `speaker_alsa_device` from
`v4l2-ctl --list-devices`, `arecord -l` and `aplay -l`. Compose maps the selected
camera/OpenCR/LiDAR devices and the ROS nodes report the configured hardware,
not a fixed `/dev/video0` or ALSA card.

## Display and browser

Set `display`, `xorg_vt`, `home_dir` and `tb3_ui_port`. Install renders the
desktop launcher for that account. Xorg, Openbox, iDesk and Epiphany are owned
by transient user services; Epiphany is single-instance guarded and tied to the
display lifecycle.

## Physical motion gate

Real motion requires a clear floor, charged base, reachable emergency stop,
valid odometry, one velocity publisher path, reviewed bounded plan and explicit
`behavior_dry_run=false`. Fresh-host validation never enables motion.
