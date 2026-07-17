import json
import os
import tempfile
import threading
import time
import wave
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray


class AsrTopicAdapter(Node):
    def __init__(self):
        super().__init__('asr_topic_adapter_node')
        self.declare_parameter('audio_topic', '/robot_audio/pcm')
        self.declare_parameter('request_topic', '/robot_asr/request')
        self.declare_parameter('text_topic', '/robot_asr/text')
        self.declare_parameter('status_topic', '/robot_asr/status')
        self.declare_parameter('model', 'auto')
        self.declare_parameter('language', 'auto')
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('channels', 1)
        self.declare_parameter('duration_sec', 5.0)

        self.model_name = str(self.get_parameter('model').value)
        self.language = str(self.get_parameter('language').value)
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.channels = int(self.get_parameter('channels').value)
        self.default_duration = float(self.get_parameter('duration_sec').value)

        audio_topic = str(self.get_parameter('audio_topic').value)
        request_topic = str(self.get_parameter('request_topic').value)
        text_topic = str(self.get_parameter('text_topic').value)
        status_topic = str(self.get_parameter('status_topic').value)

        self.text_pub = self.create_publisher(String, text_topic, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)
        self.create_subscription(UInt8MultiArray, audio_topic, self.on_audio, 10)
        self.create_subscription(String, request_topic, self.on_request, 10)

        self._lock = threading.Lock()
        self._busy = False
        self._recording = False
        self._audio = bytearray()
        self._started_at = 0.0
        self._model = None
        self._model_ready_file = Path(
            os.environ.get('SPEECH_MODEL_READY_FILE', '/tmp/tb3_asr_model_ready.json')
        )
        self._model_ready_file.unlink(missing_ok=True)
        preload_ms = self.preload_model()
        self.get_logger().info(
            f'ASR adapter ready: {audio_topic} -> {text_topic}, request={request_topic}, '
            f'model_preloaded=true, preload_ms={preload_ms}'
        )

    def preload_model(self):
        started = time.perf_counter()
        self.load_model()
        preload_ms = int((time.perf_counter() - started) * 1000)
        self._model_ready_file.parent.mkdir(parents=True, exist_ok=True)
        self._model_ready_file.write_text(
            json.dumps(
                {
                    'ready': True,
                    'engine': 'SenseVoiceSmall',
                    'languages': ['zh', 'ja', 'en'],
                    'preload_ms': preload_ms,
                    'time': time.time(),
                },
                separators=(',', ':'),
            ),
            encoding='utf-8',
        )
        return preload_ms

    def on_audio(self, msg):
        with self._lock:
            if self._recording:
                self._audio.extend(bytes(msg.data))

    def on_request(self, msg):
        duration = self.default_duration
        language = self.language
        metadata = {}
        raw = msg.data.strip()
        if raw:
            try:
                payload = json.loads(raw)
                duration = float(payload.get('duration', duration))
                language = str(payload.get('language', language))
                metadata = {
                    'request_id': str(payload.get('request_id', '') or ''),
                    'trace_id': str(payload.get('trace_id', payload.get('request_id', '')) or ''),
                    'scenario_id': payload.get('scenario_id'),
                    'trial_id': payload.get('trial_id'),
                }
            except Exception:
                try:
                    duration = float(raw)
                except ValueError:
                    language = raw
        duration = max(1.0, min(duration, 10.0))
        with self._lock:
            if self._busy:
                self.publish_status(False, 'busy', language, duration, None, 0, 0, '', metadata)
                return
            self._busy = True
            self._recording = True
            self._audio = bytearray()
            self._started_at = time.time()
        self.publish_status(True, 'recording', language, duration, None, 0, 0, '', metadata)
        threading.Thread(target=self.finish_after, args=(duration, language, metadata), daemon=True).start()

    def finish_after(self, duration, language, metadata):
        time.sleep(duration)
        with self._lock:
            audio = bytes(self._audio)
            self._recording = False
        if not audio:
            self.publish_status(False, 'no_audio', language, duration, None, 0, 0, '', metadata)
            with self._lock:
                self._busy = False
            return

        wav_path = self.write_temp_wav(audio)
        started = time.perf_counter()
        try:
            text = self.transcribe(wav_path, language, metadata)
            latency_ms = int((time.perf_counter() - started) * 1000)
            out = String()
            out.data = text
            self.text_pub.publish(out)
            self.publish_status(True, 'done', language, duration, str(wav_path), len(audio), latency_ms, text, metadata)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.publish_status(False, f'{type(exc).__name__}: {exc}', language, duration, str(wav_path), len(audio), latency_ms, '', metadata)
        finally:
            with self._lock:
                self._busy = False

    def write_temp_wav(self, audio):
        handle = tempfile.NamedTemporaryFile(prefix='tb3_asr_', suffix='.wav', delete=False)
        path = Path(handle.name)
        handle.close()
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio)
        return path

    def load_model(self, metadata=None):
        if self._model is not None:
            return self._model
        from funasr import AutoModel

        default_model_dir = Path.home() / '.cache/modelscope/hub/models/iic/SenseVoiceSmall'
        model_path = str(default_model_dir) if self.model_name == 'auto' and default_model_dir.exists() else self.model_name
        self.publish_status(True, 'loading_model', self.language, 0.0, model_path, 0, 0, '', metadata)
        self._model = AutoModel(
            model=model_path,
            trust_remote_code=True,
            vad_model=None,
            device='cpu',
            disable_update=True,
        )
        return self._model

    def transcribe(self, wav_path, language, metadata=None):
        model = self.load_model(metadata)
        result = model.generate(
            input=str(wav_path),
            cache={},
            language=None if language == 'auto' else language,
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
        )
        return self.unwrap_result(result)

    def unwrap_result(self, result):
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and 'text' in result:
            return str(result['text'])
        if isinstance(result, list) and result and isinstance(result[0], dict) and 'text' in result[0]:
            return str(result[0]['text'])
        return json.dumps(result, ensure_ascii=False)

    def publish_status(self, ok, state, language, duration, wav_path, audio_bytes, latency_ms, text, metadata=None):
        metadata = metadata or {}
        msg = String()
        msg.data = json.dumps(
            {
                'ok': ok,
                'state': state,
                'request_id': metadata.get('request_id', ''),
                'trace_id': metadata.get('trace_id', metadata.get('request_id', '')),
                'scenario_id': metadata.get('scenario_id'),
                'trial_id': metadata.get('trial_id'),
                'language': language,
                'duration': duration,
                'wav_path': wav_path,
                'audio_bytes': audio_bytes,
                'latency_ms': latency_ms,
                'text': text,
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
    node = AsrTopicAdapter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
