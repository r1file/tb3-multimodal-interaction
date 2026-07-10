from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='tb3_multimodal_interaction',
            executable='av_recorder_node',
            output='screen',
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='server_control_node',
            output='screen',
        ),
    ])
