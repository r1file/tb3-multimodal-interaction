import json
import math
import subprocess
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray


class MicCapture(Node):
    def __init__(self):
        super().__init__('mic_capture_node')
        self.declare_parameter('alsa_device', 'plughw:CARD=Device,DEV=0')
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('channels', 1)
        self.declare_parameter('chunk_ms', 200)
        self.declare_parameter('audio_topic', '/robot_audio/pcm')
        self.declare_parameter('status_topic', '/robot_audio/status')

        self.alsa_device = str(self.get_parameter('alsa_device').value)
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.channels = int(self.get_parameter('channels').value)
        self.chunk_ms = int(self.get_parameter('chunk_ms').value)
        self.chunk_bytes = max(320, int(self.sample_rate * self.channels * 2 * self.chunk_ms / 1000))

        audio_topic = str(self.get_parameter('audio_topic').value)
        status_topic = str(self.get_parameter('status_topic').value)
        self.audio_pub = self.create_publisher(UInt8MultiArray, audio_topic, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)

        self._stop_event = threading.Event()
        self._process = None
        self._worker = threading.Thread(target=self.capture_loop, daemon=True)
        self._worker.start()
        self.get_logger().info(
            f'Capturing mic {self.alsa_device} at {self.sample_rate}Hz, '
            f'{self.channels}ch -> {audio_topic}'
        )

    def capture_loop(self):
        cmd = [
            'arecord',
            '-D', self.alsa_device,
            '-f', 'S16_LE',
            '-c', str(self.channels),
            '-r', str(self.sample_rate),
            '-t', 'raw',
        ]
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except Exception as exc:
            self.publish_status({'ok': False, 'error': str(exc), 'device': self.alsa_device})
            self.get_logger().error(f'Failed to start arecord: {exc}')
            return

        last_status = 0.0
        chunks = 0
        try:
            while not self._stop_event.is_set():
                raw = self._process.stdout.read(self.chunk_bytes)
                if not raw:
                    stderr = self.read_stderr()
                    self.publish_status({'ok': False, 'error': 'arecord stopped', 'stderr': stderr})
                    break
                chunks += 1
                msg = UInt8MultiArray()
                msg.data = list(raw)
                self.audio_pub.publish(msg)

                now = time.monotonic()
                if now - last_status >= 1.0:
                    last_status = now
                    self.publish_status({
                        'ok': True,
                        'device': self.alsa_device,
                        'sample_rate': self.sample_rate,
                        'channels': self.channels,
                        'format': 'S16_LE',
                        'chunk_bytes': len(raw),
                        'chunks': chunks,
                        **self.signal_stats(raw),
                    })
        finally:
            self.stop_process()

    def signal_stats(self, raw):
        if len(raw) < 2:
            return {'rms': 0, 'rms_dbfs': '-inf', 'peak': 0}
        samples = memoryview(raw[:len(raw) - (len(raw) % 2)]).cast('h')
        if not samples:
            return {'rms': 0, 'rms_dbfs': '-inf', 'peak': 0}
        total = sum(int(sample) * int(sample) for sample in samples)
        rms = int(math.sqrt(total / len(samples)))
        peak = max(abs(int(sample)) for sample in samples)
        rms_db = 20 * math.log10(rms / 32768.0) if rms else None
        return {
            'rms': rms,
            'rms_dbfs': round(rms_db, 1) if rms_db is not None else '-inf',
            'peak': peak,
        }

    def read_stderr(self):
        if not self._process or not self._process.stderr:
            return ''
        try:
            return self._process.stderr.read().decode('utf-8', errors='ignore')[-240:]
        except Exception:
            return ''

    def publish_status(self, payload):
        msg = String()
        msg.data = json.dumps(payload, separators=(',', ':'))
        self.status_pub.publish(msg)
        if payload.get('ok'):
            self.get_logger().info(msg.data)
        else:
            self.get_logger().warn(msg.data)

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
    node = MicCapture()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
