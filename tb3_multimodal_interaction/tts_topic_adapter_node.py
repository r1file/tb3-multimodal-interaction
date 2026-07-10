import json
import re
import tempfile
import threading
import time
import wave
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray


class TtsTopicAdapter(Node):
    def __init__(self):
        super().__init__('tts_topic_adapter_node')
        self.declare_parameter('request_topic', '/robot_tts/request')
        self.declare_parameter('status_topic', '/robot_tts/status')
        self.declare_parameter('audio_topic', '/robot_speech/wav')
        self.declare_parameter('default_language', 'ja')
        self.declare_parameter('ja_voice', 'jf_alpha')
        self.declare_parameter('zh_voice', 'zf_xiaoxiao')
        self.declare_parameter('en_voice', 'af_heart')
        self.declare_parameter('sample_rate', 24000)

        request_topic = str(self.get_parameter('request_topic').value)
        status_topic = str(self.get_parameter('status_topic').value)
        audio_topic = str(self.get_parameter('audio_topic').value)

        self.default_language = str(self.get_parameter('default_language').value)
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.voices = {
            'ja': str(self.get_parameter('ja_voice').value),
            'zh': str(self.get_parameter('zh_voice').value),
            'en': str(self.get_parameter('en_voice').value),
        }

        self.audio_pub = self.create_publisher(UInt8MultiArray, audio_topic, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)
        self.create_subscription(String, request_topic, self.on_request, 10)

        self._lock = threading.Lock()
        self._busy = False
        self._pipelines = {}
        self.get_logger().info(
            f'TTS adapter ready: request={request_topic}, audio={audio_topic}, voices={self.voices}'
        )

    def on_request(self, msg):
        try:
            text, language, metadata = self.parse_request(msg.data)
        except Exception as exc:
            self.publish_status(False, 'bad_request', '', '', '', 0, 0, str(exc), metadata={})
            return
        if not text:
            self.publish_status(False, 'empty_text', language, '', '', 0, 0, '', metadata=metadata)
            return
        with self._lock:
            if self._busy:
                self.publish_status(False, 'busy', language, text, '', 0, 0, '', metadata=metadata)
                return
            self._busy = True
        threading.Thread(
            target=self.synthesize_and_publish,
            args=(text, language, metadata),
            daemon=True,
        ).start()

    def parse_request(self, raw):
        raw = raw.strip()
        language = self.default_language
        text = raw
        metadata = {}
        if raw.startswith('{'):
            payload = json.loads(raw)
            text = str(payload.get('text', '')).strip()
            language = str(payload.get('language', language)).strip() or language
            metadata = {
                'input_id': str(payload.get('input_id', '') or ''),
                'trace_id': str(payload.get('trace_id', payload.get('input_id', '')) or ''),
                'source': str(payload.get('source', '') or ''),
                'style': str(payload.get('style', '') or ''),
            }
        text = self.clean_text(text)
        language = self.normalize_language(language, text)
        return text, language, metadata

    def clean_text(self, text):
        return re.sub(r'<\|[^|]+\|>', '', str(text or '')).strip()

    def normalize_language(self, language, text):
        lang = language.lower()
        if lang in ('jp', 'jpn', 'japanese'):
            return 'ja'
        if lang in ('cn', 'zh-cn', 'mandarin', 'chinese'):
            return 'zh'
        if lang in ('en', 'eng', 'english'):
            return 'en'
        if lang in ('ja', 'zh', 'en'):
            return lang
        if any('\u3040' <= char <= '\u30ff' for char in text):
            return 'ja'
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return 'zh'
        if any(('a' <= char <= 'z') or ('A' <= char <= 'Z') for char in text):
            return 'en'
        return self.default_language

    def synthesize_and_publish(self, text, language, metadata):
        started = time.perf_counter()
        wav_path = ''
        try:
            self.publish_status(True, 'synthesizing', language, text, '', 0, 0, '', metadata=metadata)
            wav_path = str(self.synthesize(text, language, metadata))
            audio = Path(wav_path).read_bytes()
            msg = UInt8MultiArray()
            msg.data = list(audio)
            self.audio_pub.publish(msg)
            latency_ms = int((time.perf_counter() - started) * 1000)
            duration = self.wav_duration(wav_path)
            self.publish_status(
                True,
                'done',
                language,
                text,
                wav_path,
                len(audio),
                latency_ms,
                '',
                duration,
                metadata=metadata,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.publish_status(
                False,
                f'{type(exc).__name__}: {exc}',
                language,
                text,
                wav_path,
                0,
                latency_ms,
                '',
                metadata=metadata,
            )
        finally:
            if wav_path:
                try:
                    Path(wav_path).unlink(missing_ok=True)
                except Exception:
                    pass
            with self._lock:
                self._busy = False

    def get_pipeline(self, language, metadata=None):
        if language not in ('ja', 'zh', 'en'):
            raise ValueError(f'unsupported language: {language}')
        if language in self._pipelines:
            return self._pipelines[language]
        from kokoro import KPipeline

        lang_code = {'ja': 'j', 'zh': 'z', 'en': 'a'}[language]
        self.publish_status(True, 'loading_model', language, '', '', 0, 0, '', metadata=metadata)
        self._pipelines[language] = KPipeline(lang_code=lang_code)
        return self._pipelines[language]

    def synthesize(self, text, language, metadata=None):
        pipeline = self.get_pipeline(language, metadata=metadata)
        voice = self.voices[language]
        chunks = []
        for _, _, audio in pipeline(text, voice=voice):
            chunks.append(audio)
        if not chunks:
            raise RuntimeError('kokoro returned no audio chunks')
        if len(chunks) == 1:
            audio = chunks[0]
        else:
            import numpy as np

            audio = np.concatenate(chunks)

        import soundfile as sf

        handle = tempfile.NamedTemporaryFile(prefix='tb3_tts_', suffix='.wav', delete=False)
        path = Path(handle.name)
        handle.close()
        sf.write(str(path), audio, self.sample_rate)
        return path

    def wav_duration(self, path):
        with wave.open(str(path), 'rb') as wav:
            return wav.getnframes() / float(wav.getframerate())

    def publish_status(
        self,
        ok,
        state,
        language,
        text,
        wav_path,
        audio_bytes,
        latency_ms,
        error,
        duration=0.0,
        metadata=None,
    ):
        metadata = metadata or {}
        msg = String()
        msg.data = json.dumps(
            {
                'ok': ok,
                'state': state,
                'input_id': metadata.get('input_id', ''),
                'trace_id': metadata.get('trace_id', metadata.get('input_id', '')),
                'source': metadata.get('source', ''),
                'style': metadata.get('style', ''),
                'language': language,
                'voice': self.voices.get(language, ''),
                'text': text,
                'wav_path': wav_path,
                'audio_bytes': audio_bytes,
                'latency_ms': latency_ms,
                'audio_duration_s': duration,
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
    node = TtsTopicAdapter()
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
