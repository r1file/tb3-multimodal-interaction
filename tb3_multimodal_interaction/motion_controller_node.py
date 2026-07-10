import json
import threading
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from std_msgs.msg import Bool, String


class MotionController(Node):
    def __init__(self):
        super().__init__('motion_controller_node')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('max_linear_x', 0.10)
        self.declare_parameter('max_angular_z', 0.50)
        self.declare_parameter('default_duration', 0.6)
        self.declare_parameter('max_duration', 1.5)
        self.declare_parameter('publish_hz', 20.0)

        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.max_linear_x = float(self.get_parameter('max_linear_x').value)
        self.max_angular_z = float(self.get_parameter('max_angular_z').value)
        self.default_duration = float(self.get_parameter('default_duration').value)
        self.max_duration = float(self.get_parameter('max_duration').value)
        self.publish_hz = float(self.get_parameter('publish_hz').value)

        self._stop_event = threading.Event()
        self._worker = None
        self._lock = threading.Lock()

        self.publisher = self.create_publisher(TwistStamped, cmd_vel_topic, 10)
        self.create_subscription(String, '/robot_motion/action_cmd', self.on_action, 10)
        self.create_subscription(Bool, '/emergency_stop', self.on_emergency_stop, 10)
        self.get_logger().info(f'Publishing TwistStamped to {cmd_vel_topic}')

    def on_emergency_stop(self, msg):
        if msg.data:
            self.get_logger().warn('Emergency stop received')
            self._stop_event.set()
            self.publish_stop()

    def on_action(self, msg):
        try:
            command = self.parse_command(msg.data)
        except ValueError as exc:
            self.get_logger().warn(f'Invalid motion command: {exc}')
            self.publish_stop()
            return

        with self._lock:
            self._stop_event.set()
            if self._worker and self._worker.is_alive():
                self._worker.join(timeout=0.2)
            self._stop_event.clear()
            self._worker = threading.Thread(target=self.execute_motion, args=(command,), daemon=True)
            self._worker.start()

    def parse_command(self, data):
        data = data.strip()
        if not data:
            raise ValueError('empty command')
        if data.startswith('{'):
            payload = json.loads(data)
            action = str(payload.get('action', '')).strip()
            duration = float(payload.get('duration', self.default_duration))
        else:
            action = data
            duration = self.default_duration
        linear_x, angular_z = self.velocity_for_action(action)
        duration = max(0.0, min(duration, self.max_duration))
        return {'action': action, 'linear_x': linear_x, 'angular_z': angular_z, 'duration': duration}

    def velocity_for_action(self, action):
        table = {
            'move_forward_slow': (0.06, 0.0),
            'move_backward': (-0.04, 0.0),
            'turn_left': (0.0, 0.35),
            'turn_right': (0.0, -0.35),
            'stop': (0.0, 0.0),
        }
        if action == 'look_around':
            return (0.0, 0.30)
        if action not in table:
            raise ValueError(f'unknown action {action!r}')
        return table[action]

    def execute_motion(self, command):
        action = command['action']
        duration = command['duration']
        self.get_logger().info(f'Executing {action} for {duration:.2f}s')
        if action == 'stop' or duration == 0.0:
            self.publish_stop()
            return
        if action == 'look_around':
            self.run_segment(0.0, 0.30, min(duration, self.max_duration) / 2.0)
            self.run_segment(0.0, -0.30, min(duration, self.max_duration) / 2.0)
        else:
            self.run_segment(command['linear_x'], command['angular_z'], duration)
        self.publish_stop()

    def run_segment(self, linear_x, angular_z, duration):
        linear_x = max(-self.max_linear_x, min(self.max_linear_x, linear_x))
        angular_z = max(-self.max_angular_z, min(self.max_angular_z, angular_z))
        period = 1.0 / self.publish_hz
        end = time.monotonic() + duration
        while time.monotonic() < end and not self._stop_event.is_set():
            self.publish_twist(linear_x, angular_z)
            time.sleep(period)

    def publish_twist(self, linear_x, angular_z):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.twist.linear.x = float(linear_x)
        msg.twist.angular.z = float(angular_z)
        self.publisher.publish(msg)

    def publish_stop(self):
        self.publish_twist(0.0, 0.0)


def main(args=None):
    rclpy.init(args=args)
    node = MotionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
