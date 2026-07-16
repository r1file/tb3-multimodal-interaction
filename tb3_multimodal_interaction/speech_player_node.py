import json
import os
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray


class SpeechPlayer(Node):
    def __init__(self):
        super().__init__('speech_player_node')
        self.declare_parameter('alsa_device', 'plughw:CARD=UACDemoV10,DEV=0')
        self.declare_parameter('playback_timeout_margin_sec', 5.0)
        self.declare_parameter('min_playback_timeout_sec', 8.0)
        self.alsa_device = str(self.get_parameter('alsa_device').value)
        self.playback_timeout_margin_sec = float(self.get_parameter('playback_timeout_margin_sec').value)
        self.min_playback_timeout_sec = float(self.get_parameter('min_playback_timeout_sec').value)
        self.status_pub = self.create_publisher(String, '/robot_speech/status', 10)
        self.create_subscription(String, '/robot_speech/text', self.on_speech, 10)
        self.create_subscription(String, '/robot_speech/metadata', self.on_metadata, 10)
        self.create_subscription(UInt8MultiArray, '/robot_speech/wav', self.on_wav, 10)
        self._audio_metadata = {}
        self.get_logger().info(f'Speaker output target: {self.alsa_device}')

    def on_metadata(self, msg):
        try:
            payload = json.loads(msg.data or '{}')
            self._audio_metadata = payload if isinstance(payload, dict) else {}
        except Exception as exc:
            self._audio_metadata = {}
            self.get_logger().warn(f'ignored malformed speech metadata: {exc}')

    def on_speech(self, msg):
        data = msg.data.strip()
        if not data:
            self.publish_status('ignored', False, 'empty speech command')
            return
        if data.startswith('file:'):
            path = data[5:].strip()
            self.play_file(path, metadata={})
        elif os.path.exists(data):
            self.play_file(data, metadata={})
        else:
            self.play_test_tone(data, metadata={})

    def on_wav(self, msg):
        audio = bytes(msg.data)
        metadata = dict(self._audio_metadata)
        self._audio_metadata = {}
        if not audio:
            self.publish_status('ignored', False, 'empty wav command', metadata=metadata)
            return
        handle = tempfile.NamedTemporaryFile(prefix='tb3_speech_', suffix='.wav', delete=False)
        path = Path(handle.name)
        try:
            handle.write(audio)
            handle.close()
            self.play_file(path, metadata=metadata)
        finally:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    def play_file(self, path, metadata=None):
        audio_path = Path(path)
        if not audio_path.exists():
            self.publish_status('failed', False, f'missing file {audio_path}', metadata=metadata)
            return
        cmd = ['aplay', '-D', self.alsa_device, str(audio_path)]
        duration = self.wav_duration(audio_path)
        timeout = max(self.min_playback_timeout_sec, duration + self.playback_timeout_margin_sec)
        self.run_command(cmd, f'file {audio_path.name}', timeout=timeout, metadata=metadata)

    def play_test_tone(self, label, metadata=None):
        cmd = ['speaker-test', '-D', self.alsa_device, '-c', '2', '-r', '48000', '-t', 'sine', '-f', '880', '-l', '1']
        self.run_command(cmd, f'test tone for {label!r}', metadata=metadata)

    def run_command(self, cmd, label, timeout=8.0, metadata=None):
        started = time.perf_counter()
        self.publish_status('start', True, label, metadata=metadata)
        self.get_logger().info('Running: ' + ' '.join(cmd) + f' timeout={timeout:.1f}s')
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if result.returncode == 0:
                self.publish_status('done', True, label, latency_ms, metadata=metadata)
            else:
                self.publish_status(
                    'failed',
                    False,
                    label,
                    latency_ms,
                    f'rc={result.returncode} {result.stderr[-160:]}',
                    metadata,
                )
        except Exception as exc:
            self.publish_status(
                'error',
                False,
                label,
                int((time.perf_counter() - started) * 1000),
                str(exc),
                metadata,
            )

    def wav_duration(self, path):
        try:
            with wave.open(str(path), 'rb') as wav:
                return wav.getnframes() / float(wav.getframerate())
        except Exception as exc:
            self.get_logger().warn(f'failed to read wav duration for {path}: {exc}')
            return 0.0

    def publish_status(self, state, ok, label, latency_ms=0, error='', metadata=None):
        metadata = metadata or {}
        msg = String()
        msg.data = json.dumps(
            {
                'ok': ok,
                'state': state,
                'input_id': metadata.get('input_id', ''),
                'trace_id': metadata.get('trace_id', metadata.get('input_id', '')),
                'source': metadata.get('source', ''),
                'language': metadata.get('language', ''),
                'label': label,
                'latency_ms': latency_ms,
                'error': error,
                'time': time.time(),
            },
            ensure_ascii=False,
            separators=(',', ':'),
        )
        self.status_pub.publish(msg)
        if ok:
            self.get_logger().info(msg.data)
        else:
            self.get_logger().warn(msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = SpeechPlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
