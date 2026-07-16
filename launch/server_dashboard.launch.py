import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    dashboard_port = int(os.environ.get('SERVER_DASHBOARD_PORT', '8775'))
    tb3_ip = os.environ.get('TB3_IP', '192.168.250.10')
    tb3_ui_port = int(os.environ.get('TB3_UI_PORT', '8765'))

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
            parameters=[{
                'port': dashboard_port,
                'face_state_url': f'http://{tb3_ip}:{tb3_ui_port}/state.json',
            }],
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='evaluation_logger_node',
            output='screen',
        ),
    ])
