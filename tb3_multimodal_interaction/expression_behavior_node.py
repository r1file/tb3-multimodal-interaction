import json
import threading
import time
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from std_msgs.msg import String
import yaml


class ExpressionBehavior(Node):
    def __init__(self):
        super().__init__('expression_behavior_node')
        default_config = str(
            Path(get_package_share_directory('tb3_multimodal_interaction'))
            / 'config'
            / 'expression_behaviors.yaml'
        )
        self.declare_parameter('config_path', default_config)
        self.declare_parameter('motion_gap_sec', 0.08)
        self.config_path = Path(str(self.get_parameter('config_path').value))
        self.motion_gap_sec = float(self.get_parameter('motion_gap_sec').value)
        self.behaviors = self.load_behaviors()

        self.face_pub = self.create_publisher(String, '/robot_face/expression', 10)
        self.motion_pub = self.create_publisher(String, '/robot_motion/action_cmd', 10)
        self.status_pub = self.create_publisher(String, '/robot_expression/status', 10)
        self.create_subscription(String, '/robot_expression/trigger', self.on_trigger, 10)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker = None
        self.get_logger().info(f'Loaded expression behaviors from {self.config_path}')

    def load_behaviors(self):
        try:
            with self.config_path.open('r', encoding='utf-8') as handle:
                payload = yaml.safe_load(handle) or {}
        except Exception as exc:
            self.get_logger().error(f'Failed to load behavior config: {exc}')
            payload = {}
        expressions = payload.get('expressions', {})
        if not expressions:
            expressions = {'neutral': {'face': 'neutral', 'motions': [{'action': 'stop', 'duration': 0.0}]}}
        return expressions

    def on_trigger(self, msg):
        expression = msg.data.strip() or 'neutral'
        if expression not in self.behaviors:
            self.publish_status(False, expression, f'unknown expression {expression!r}')
            expression = 'neutral'
        with self._lock:
            self._stop_event.set()
            if self._worker and self._worker.is_alive():
                self._worker.join(timeout=0.3)
            self._stop_event.clear()
            self._worker = threading.Thread(target=self.run_behavior, args=(expression,), daemon=True)
            self._worker.start()

    def run_behavior(self, expression):
        behavior = self.behaviors.get(expression, self.behaviors['neutral'])
        face = str(behavior.get('face', expression))
        self.publish_string(self.face_pub, face)
        self.publish_status(True, expression, 'started')

        for motion in behavior.get('motions', []):
            if self._stop_event.is_set():
                break
            action = str(motion.get('action', 'stop'))
            duration = max(0.0, float(motion.get('duration', 0.0)))
            payload = json.dumps({'action': action, 'duration': duration}, separators=(',', ':'))
            self.publish_string(self.motion_pub, payload)
            time.sleep(duration + self.motion_gap_sec)

        self.publish_string(self.motion_pub, 'stop')
        self.publish_status(True, expression, 'finished')

    def publish_string(self, publisher, value):
        msg = String()
        msg.data = value
        publisher.publish(msg)

    def publish_status(self, ok, expression, state):
        msg = String()
        msg.data = json.dumps(
            {'ok': ok, 'expression': expression, 'state': state, 'time': time.time()},
            separators=(',', ':'),
        )
        self.status_pub.publish(msg)
        if ok:
            self.get_logger().info(msg.data)
        else:
            self.get_logger().warn(msg.data)

    def destroy_node(self):
        self._stop_event.set()
        self.publish_string(self.motion_pub, 'stop')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ExpressionBehavior()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
