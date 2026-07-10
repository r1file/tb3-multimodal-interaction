from glob import glob
import os

from setuptools import find_packages, setup


package_name = 'tb3_multimodal_interaction'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'scripts'), glob('scripts/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='cuibaitao',
    maintainer_email='cuibaitao@example.com',
    description='TurtleBot3 multimodal interaction, behavior, and device nodes.',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'motion_controller_node = tb3_multimodal_interaction.motion_controller_node:main',
            'face_display_node = tb3_multimodal_interaction.face_display_node:main',
            'expression_behavior_node = tb3_multimodal_interaction.expression_behavior_node:main',
            'camera_capture_node = tb3_multimodal_interaction.camera_capture_node:main',
            'mic_capture_node = tb3_multimodal_interaction.mic_capture_node:main',
            'speech_player_node = tb3_multimodal_interaction.speech_player_node:main',
            'av_recorder_node = tb3_multimodal_interaction.av_recorder_node:main',
            'asr_topic_adapter_node = tb3_multimodal_interaction.asr_topic_adapter_node:main',
            'tts_topic_adapter_node = tb3_multimodal_interaction.tts_topic_adapter_node:main',
            'server_control_node = tb3_multimodal_interaction.server_control_node:main',
            'behavior_executor_node = tb3_multimodal_interaction.behavior_executor_node:main',
            'vlm_behavior_client_node = tb3_multimodal_interaction.vlm_behavior_client_node:main',
            'io_test_sequence = tb3_multimodal_interaction.io_test_sequence:main',
        ],
    },
)
