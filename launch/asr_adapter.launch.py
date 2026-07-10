from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='tb3_multimodal_interaction',
            executable='asr_topic_adapter_node',
            output='screen',
            parameters=[
                {
                    'audio_topic': '/robot_audio/pcm',
                    'request_topic': '/robot_asr/request',
                    'text_topic': '/robot_asr/text',
                    'status_topic': '/robot_asr/status',
                    'model': 'auto',
                    'language': 'auto',
                    'sample_rate': 16000,
                    'channels': 1,
                    'duration_sec': 5.0,
                }
            ],
        ),
    ])
