import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Week2TestSequence(Node):
    def __init__(self):
        super().__init__('io_test_sequence')
        self.motion_pub = self.create_publisher(String, '/robot_motion/action_cmd', 10)
        self.face_pub = self.create_publisher(String, '/robot_face/expression', 10)
        self.speech_pub = self.create_publisher(String, '/robot_speech/text', 10)

    def publish(self, publisher, data):
        msg = String()
        msg.data = data
        publisher.publish(msg)
        self.get_logger().info(f'Published {data}')

    def run(self):
        time.sleep(1.0)
        self.publish(self.face_pub, 'happy')
        time.sleep(0.5)
        self.publish(self.speech_pub, 'TB3 speaker test')
        time.sleep(1.0)
        self.publish(self.motion_pub, '{"action":"turn_left","duration":0.5}')
        time.sleep(1.0)
        self.publish(self.motion_pub, 'stop')
        self.publish(self.face_pub, 'neutral')


def main(args=None):
    rclpy.init(args=args)
    node = Week2TestSequence()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
