import os

from launch import LaunchDescription
from launch_ros.actions import Node


def _env_bool(name):
    value = os.environ[name]
    return value.strip().lower() in ("1", "true", "yes", "on")


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="tb3_multimodal_interaction",
            executable="behavior_executor_node",
            output="screen",
            parameters=[{
                "dry_run": _env_bool("TB3_BEHAVIOR_DRY_RUN"),
                "max_duration": float(os.environ["TB3_BEHAVIOR_MAX_DURATION"]),
                "motion_gap_sec": float(os.environ["TB3_BEHAVIOR_MOTION_GAP_S"]),
            }],
        ),
    ])
