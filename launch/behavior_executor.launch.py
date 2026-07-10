import os

from launch import LaunchDescription
from launch_ros.actions import Node


def _env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="tb3_multimodal_interaction",
            executable="behavior_executor_node",
            output="screen",
            parameters=[{
                "dry_run": _env_bool("TB3_BEHAVIOR_DRY_RUN", True),
                "max_duration": float(os.environ.get("TB3_BEHAVIOR_MAX_DURATION", "1.5")),
                "motion_gap_sec": float(os.environ.get("TB3_BEHAVIOR_MOTION_GAP_SEC", "0.08")),
            }],
        ),
    ])
