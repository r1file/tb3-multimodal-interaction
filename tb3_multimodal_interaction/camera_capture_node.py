import json
import subprocess
import threading
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String


class CameraCapture(Node):
    def __init__(self):
        super().__init__('camera_capture_node')
        self.declare_parameter('device', '/dev/video0')
        self.declare_parameter('image_topic', '/robot_camera/jpeg')
        self.declare_parameter('status_topic', '/robot_camera/status')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 5)
        self.declare_parameter('jpeg_quality', 5)

        self.device = str(self.get_parameter('device').value)
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = int(self.get_parameter('fps').value)
        self.jpeg_quality = int(self.get_parameter('jpeg_quality').value)
        image_topic = str(self.get_parameter('image_topic').value)
        status_topic = str(self.get_parameter('status_topic').value)

        self.image_pub = self.create_publisher(CompressedImage, image_topic, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)
        self._stop_event = threading.Event()
        self._process = None
        self._worker = threading.Thread(target=self.capture_loop, daemon=True)
        self._worker.start()
        self.get_logger().info(
            f'Capturing {self.device} at {self.width}x{self.height}@{self.fps} -> {image_topic}'
        )

    def capture_loop(self):
        if not Path(self.device).exists():
            self.publish_status(False, f'{self.device} missing')
            return

        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel',
            'warning',
            '-f',
            'video4linux2',
            '-framerate',
            str(self.fps),
            '-video_size',
            f'{self.width}x{self.height}',
            '-i',
            self.device,
            '-q:v',
            str(self.jpeg_quality),
            '-f',
            'image2pipe',
            '-vcodec',
            'mjpeg',
            '-',
        ]
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except Exception as exc:
            self.publish_status(False, f'failed to start ffmpeg: {exc}')
            return

        buffer = bytearray()
        frames = 0
        last_status = 0.0
        try:
            while not self._stop_event.is_set():
                chunk = self._process.stdout.read(4096)
                if not chunk:
                    stderr = self.read_stderr()
                    self.publish_status(False, f'ffmpeg stopped: {stderr}')
                    break
                buffer.extend(chunk)
                while True:
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9', start + 2) if start >= 0 else -1
                    if start < 0:
                        buffer.clear()
                        break
                    if end < 0:
                        if start:
                            del buffer[:start]
                        break
                    frame = bytes(buffer[start:end + 2])
                    del buffer[:end + 2]
                    self.publish_frame(frame)
                    frames += 1
                    now = time.monotonic()
                    if now - last_status >= 2.0:
                        last_status = now
                        self.publish_status(True, f'frames={frames}')
        finally:
            self.stop_process()

    def publish_frame(self, data):
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.format = 'jpeg'
        msg.data = data
        self.image_pub.publish(msg)

    def publish_status(self, ok, state):
        msg = String()
        msg.data = json.dumps(
            {
                'ok': ok,
                'device': self.device,
                'width': self.width,
                'height': self.height,
                'fps': self.fps,
                'state': state,
                'time': time.time(),
            },
            separators=(',', ':'),
        )
        self.status_pub.publish(msg)
        if ok:
            self.get_logger().info(msg.data)
        else:
            self.get_logger().warn(msg.data)

    def read_stderr(self):
        if not self._process or not self._process.stderr:
            return ''
        try:
            return self._process.stderr.read().decode('utf-8', errors='ignore')[-240:]
        except Exception:
            return ''

    def stop_process(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def destroy_node(self):
        self._stop_event.set()
        self.stop_process()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraCapture()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
