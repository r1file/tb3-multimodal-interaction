import json
import shutil
import subprocess
import threading
import time
import wave
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String, UInt8MultiArray


class AvRecorder(Node):
    def __init__(self):
        super().__init__('av_recorder_node')
        self.declare_parameter('output_dir', '/workspace/ros2_ws/artifacts/multimodal_av')
        self.declare_parameter('duration_sec', 5.0)
        self.declare_parameter('camera_topic', '/robot_camera/jpeg')
        self.declare_parameter('audio_topic', '/robot_audio/pcm')
        self.declare_parameter('request_topic', '/robot_av/record_request')
        self.declare_parameter('status_topic', '/robot_av/status')
        self.declare_parameter('audio_rate', 16000)
        self.declare_parameter('audio_channels', 1)

        self.output_dir = Path(str(self.get_parameter('output_dir').value))
        self.duration_sec = float(self.get_parameter('duration_sec').value)
        self.audio_rate = int(self.get_parameter('audio_rate').value)
        self.audio_channels = int(self.get_parameter('audio_channels').value)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        camera_topic = str(self.get_parameter('camera_topic').value)
        audio_topic = str(self.get_parameter('audio_topic').value)
        request_topic = str(self.get_parameter('request_topic').value)
        status_topic = str(self.get_parameter('status_topic').value)

        self.status_pub = self.create_publisher(String, status_topic, 10)
        self.create_subscription(CompressedImage, camera_topic, self.on_frame, 10)
        self.create_subscription(UInt8MultiArray, audio_topic, self.on_audio, 10)
        self.create_subscription(String, request_topic, self.on_request, 10)

        self._lock = threading.Lock()
        self._recording = False
        self._frames = []
        self._audio = bytearray()
        self._started_at = 0.0
        self.get_logger().info(f'AV recorder ready in {self.output_dir}')

    def on_frame(self, msg):
        with self._lock:
            if self._recording:
                self._frames.append(bytes(msg.data))

    def on_audio(self, msg):
        with self._lock:
            if self._recording:
                self._audio.extend(bytes(msg.data))

    def on_request(self, msg):
        duration = self.duration_sec
        label = 'multimodal'
        text = msg.data.strip()
        if text:
            try:
                payload = json.loads(text)
                duration = float(payload.get('duration', duration))
                label = str(payload.get('label', label))
            except Exception:
                try:
                    duration = float(text)
                except ValueError:
                    label = text
        duration = max(1.0, min(duration, 10.0))
        with self._lock:
            if self._recording:
                self.publish_status(False, 'busy', None, 0, 0)
                return
            self._recording = True
            self._frames = []
            self._audio = bytearray()
            self._started_at = time.time()
        self.publish_status(True, 'recording', None, 0, 0)
        thread = threading.Thread(target=self.finish_after, args=(duration, label), daemon=True)
        thread.start()

    def finish_after(self, duration, label):
        time.sleep(duration)
        with self._lock:
            frames = list(self._frames)
            audio = bytes(self._audio)
            self._recording = False

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        safe_label = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in label)[:40] or 'multimodal'
        work_dir = self.output_dir / f'{timestamp}_{safe_label}'
        work_dir.mkdir(parents=True, exist_ok=True)
        frame_dir = work_dir / 'frames'
        frame_dir.mkdir()

        for index, frame in enumerate(frames):
            (frame_dir / f'frame_{index:05d}.jpg').write_bytes(frame)

        raw_path = work_dir / 'audio.raw'
        wav_path = work_dir / 'audio.wav'
        mp4_path = work_dir / 'multimodal_av_test.mp4'
        raw_path.write_bytes(audio)
        self.write_wav(wav_path, audio)

        if not frames or not audio:
            self.publish_status(False, 'missing frames or audio', str(work_dir), len(frames), len(audio))
            return

        ok, detail = self.make_mp4(frame_dir, raw_path, mp4_path)
        if ok:
            self.publish_status(True, 'saved', str(mp4_path), len(frames), len(audio))
        else:
            self.publish_status(False, detail, str(work_dir), len(frames), len(audio))

    def write_wav(self, path, audio):
        with wave.open(str(path), 'wb') as handle:
            handle.setnchannels(self.audio_channels)
            handle.setsampwidth(2)
            handle.setframerate(self.audio_rate)
            handle.writeframes(audio)

    def make_mp4(self, frame_dir, raw_path, mp4_path):
        if not shutil.which('ffmpeg'):
            return False, 'ffmpeg missing'
        cmd = [
            'ffmpeg',
            '-y',
            '-hide_banner',
            '-loglevel',
            'error',
            '-framerate',
            '5',
            '-pattern_type',
            'glob',
            '-i',
            str(frame_dir / 'frame_*.jpg'),
            '-f',
            's16le',
            '-ar',
            str(self.audio_rate),
            '-ac',
            str(self.audio_channels),
            '-i',
            str(raw_path),
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            '-c:a',
            'aac',
            '-shortest',
            str(mp4_path),
        ]
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=30, check=False)
        if result.returncode != 0:
            return False, result.stderr[-240:] or 'ffmpeg failed'
        return True, 'saved'

    def publish_status(self, ok, state, path, frame_count, audio_bytes):
        msg = String()
        msg.data = json.dumps(
            {
                'ok': ok,
                'state': state,
                'path': path,
                'frames': frame_count,
                'audio_bytes': audio_bytes,
                'time': time.time(),
            },
            separators=(',', ':'),
        )
        self.status_pub.publish(msg)
        if ok:
            self.get_logger().info(msg.data)
        else:
            self.get_logger().warn(msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = AvRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
