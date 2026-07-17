from launch import LaunchDescription
from launch.substitutions import EnvironmentVariable
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="tb3_multimodal_interaction",
                executable="vlm_behavior_client_node",
                name="vlm_behavior_client_node",
                output="screen",
                parameters=[
                    {
                        "llama_base_url": EnvironmentVariable("VLM_BASE_URL"),
                        "model": EnvironmentVariable("VLM_MODEL"),
                        "publish_plans": EnvironmentVariable(
                            "VLM_PUBLISH_PLANS",
                            default_value="true",
                        ),
                        "log_dir": EnvironmentVariable(
                            "VLM_LOG_DIR",
                            default_value="/tmp/vlm_client_logs",
                        ),
                    }
                ],
            )
        ]
    )
