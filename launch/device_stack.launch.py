import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cmd_vel_topic = os.environ['TB3_CMD_VEL_TOPIC']
    ui_port = int(os.environ['TB3_UI_PORT'])
    camera_device = os.environ['TB3_CAMERA_DEVICE']
    mic_device = os.environ['TB3_MIC_ALSA_DEVICE']
    speaker_device = os.environ['TB3_SPEAKER_ALSA_DEVICE']

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
            parameters=[{
                'port': ui_port,
                'camera_device': camera_device,
                'mic_alsa_device': mic_device,
                'speaker_alsa_device': speaker_device,
            }],
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='camera_capture_node',
            output='screen',
            parameters=[{'device': camera_device}],
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='mic_capture_node',
            output='screen',
            parameters=[{'alsa_device': mic_device}],
        ),
        Node(
            package='tb3_multimodal_interaction',
            executable='speech_player_node',
            output='screen',
            parameters=[{'alsa_device': speaker_device}],
        ),
    ])
