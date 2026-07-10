import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cmd_vel_topic = os.environ.get('TB3_CMD_VEL_TOPIC', '/robot_a/cmd_vel')

    return LaunchDescription([
        Node(
            package='tb3_multimodal_interaction',
            executable='motion_controller_node',
            output='screen',
            parameters=[{'cmd_vel_topic': cmd_vel_topic}],
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='expression_behavior_node',
            output='screen',
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='face_display_node',
            output='screen',
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='camera_capture_node',
            output='screen',
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='mic_capture_node',
            output='screen',
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='speech_player_node',
            output='screen',
        ),
    ])
