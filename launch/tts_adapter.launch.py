from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='tb3_multimodal_interaction',
            executable='tts_topic_adapter_node',
            name='tts_topic_adapter_node',
            output='screen',
        ),
    ])
