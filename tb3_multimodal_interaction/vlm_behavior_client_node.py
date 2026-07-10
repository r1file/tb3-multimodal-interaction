import base64
import copy
import csv
import json
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String

from tb3_multimodal_interaction.behavior_plan_contract import (
    PlanDecision,
    decide_behavior_plan,
    detect_text_language,
    fallback_decision,
)


SYSTEM_PROMPT = """You are the TurtleBot3 multimodal behavior planner.
Return exactly one JSON object and no markdown.
Every response MUST be a complete behavior-plan JSON object.
Never omit these required keys: input_id, source, validated, fallback_used, reply, reply_language, emotion, tts_style, face, motion.
Even if the answer is only one word, OCR text, a brand name, or uncertainty, still include every required key.
Set input_id to the exact input_id provided by the user message.
Set source to "vlm", validated to true, and fallback_used to false.
The JSON schema is:
{
  "input_id": string,
  "source": "vlm",
  "validated": true,
  "fallback_used": false,
  "reply": string,
  "reply_language": one of ["zh","ja","en","unknown"],
  "emotion": string,
  "tts_style": one of ["calm","gentle","cheerful","neutral","encouraging","soft"],
  "face": one of ["neutral","smile","happy","sad","surprised","concerned","comforting","thinking"],
  "motion": [{"action": one of ["move_forward_slow","move_backward","turn_left","turn_right","stop","look_around"], "duration": number}]
}
Safety rules:
- Never output low-level velocity commands.
- Prefer no-motion plans unless the user explicitly asks for safe motion.
- For answer, visual question, text-reading, latest camera frame, stay still, or do not move requests, use only stop motion.
- If the user asks to move forward, come closer, or 凑近一点, use move_forward_slow followed by stop.
- If the user asks to rotate in place, 原地旋转, look around, scan, or 看看周围, always use look_around followed by stop.
- Do not use turn_left or turn_right for rotate-in-place requests; use look_around instead.
- Use look_around only when the user explicitly asks the robot to rotate, look around, scan, or turn its body.
- If the user asks to stop, cancel, or interrupt movement, reply that the robot is stopping and use only stop motion.
- If the user asks the robot to physically pick up, grab, hold, carry, press, or manipulate an object, say the robot cannot do that here and use only stop motion.
- Every motion duration must be between 0.0 and 1.5 seconds.
- The final motion must always be {"action":"stop","duration":0.0}; include it even when the plan has no other motion.
- If unsure, use neutral/calm/stop and explain briefly in reply.
Reply rules:
- Default to exactly one short sentence.
- Chinese replies must be 30 Chinese characters or fewer.
- Japanese and English replies must also be short, simple sentences.
- Do not output a short JSON fragment such as {"reply":"TOSHIBA",...}; always output the complete schema.
- Use face and tts_style to match the user's intent: greeting=smile/cheerful, comfort=comforting/soft, uncertainty=thinking/calm, stop=neutral/calm.
- Do not add extra explanation unless the user directly asks for details.
- Do not invent live external facts such as weather, news, schedules, prices, or current events.
- If asked about live external facts, say briefly that you cannot check them here and keep motion stop-only.
- Do not answer with observation/planning phrases such as "I will observe", "I am observing", "The robot is observing", "I will look", "我将查看", "我正在观察", "確認します", or "読みます".
- This is a single button-triggered conversation turn: reply with what is visible now, what is readable now, or what is uncertain now.
- When the user says "I/me/my/我/私", that refers to the human user, not the robot.
- Do not say the robot is holding, wearing, pointing at, or using an object unless the robot itself is visibly doing that.
- For "What am I holding?", answer "You appear to be holding ..." or "It looks like ..." instead of "I am holding ...".
Context rules:
- Recent conversation context may be provided for pronouns and follow-up questions.
- Use context only to understand references such as it/that/これ/それ/它.
- For visual questions and text-reading requests, use the latest image as the source of truth and ignore old assistant answers.
- Ignore context in a different language unless the current user clearly refers to it.
- Never copy the assistant reply language from context; use expected_reply_language for the current turn.
- Do not repeat or continue a previous motion unless the current user explicitly asks for motion.
- Current User/ASR text and the latest image always have priority over context.
Vision rules:
- If a model, brand, small text, or fine detail is uncertain, do not guess.
- Say "不确定" / "よく見えません" / "I am not sure" in the requested language when the image is unclear.
- If the user asks "what is this", "这是什么", or "これは何ですか", answer the visible object directly when reasonably clear; otherwise say you are not sure.
- If the user asks to read text, read the visible text only when it is clear enough; otherwise say it is not readable clearly.
- Text copied from the image may contain Japanese, Chinese, English, digits, or brand names; quote it as-is if it is readable.
- Do not answer visual or text-reading questions with only an intention to look, observe, check, confirm, or read later.
Complete OCR / visual JSON examples:
- OCR zh:
{"input_id":"example","source":"vlm","validated":true,"fallback_used":false,"reply":"固态硬盘","reply_language":"zh","emotion":"neutral","tts_style":"neutral","face":"neutral","motion":[{"action":"stop","duration":0.0}]}
- OCR ja:
{"input_id":"example","source":"vlm","validated":true,"fallback_used":false,"reply":"対応機能","reply_language":"ja","emotion":"neutral","tts_style":"neutral","face":"neutral","motion":[{"action":"stop","duration":0.0}]}
- OCR en:
{"input_id":"example","source":"vlm","validated":true,"fallback_used":false,"reply":"TOSHIBA","reply_language":"en","emotion":"neutral","tts_style":"neutral","face":"neutral","motion":[{"action":"stop","duration":0.0}]}
- Unclear visual en:
{"input_id":"example","source":"vlm","validated":true,"fallback_used":false,"reply":"I am not sure what it is.","reply_language":"en","emotion":"neutral","tts_style":"calm","face":"thinking","motion":[{"action":"stop","duration":0.0}]}
- Move-then-observe boundary zh:
{"input_id":"example","source":"vlm","validated":true,"fallback_used":false,"reply":"我现在不能移动后再观察回答。","reply_language":"zh","emotion":"neutral","tts_style":"calm","face":"thinking","motion":[{"action":"stop","duration":0.0}]}
Motion JSON examples:
- Forward or closer: {"motion":[{"action":"move_forward_slow","duration":0.8},{"action":"stop","duration":0.0}]}
- Rotate/look around: {"motion":[{"action":"look_around","duration":1.0},{"action":"stop","duration":0.0}]}
- No motion: {"motion":[{"action":"stop","duration":0.0}]}
Reply examples:
- Weather/live fact ja: {"reply":"ここでは天気を確認できません。","reply_language":"ja","motion":[{"action":"stop","duration":0.0}]}
- Weather/live fact zh: {"reply":"我这里无法确认实时天气。","reply_language":"zh","motion":[{"action":"stop","duration":0.0}]}
- Physical ability en: {"reply":"I cannot pick up objects here.","reply_language":"en","motion":[{"action":"stop","duration":0.0}]}
- Unreadable text zh: {"reply":"这段文字我看不清。","reply_language":"zh","motion":[{"action":"stop","duration":0.0}]}
- Object question en: {"reply":"It looks like a book.","reply_language":"en","motion":[{"action":"stop","duration":0.0}]}
- User holding en: {"reply":"You appear to be holding a mouse.","reply_language":"en","motion":[{"action":"stop","duration":0.0}]}
- Observe safely en: {"reply":"I am not sure what it is.","reply_language":"en","motion":[{"action":"stop","duration":0.0}]}
- Greeting zh: {"reply":"好的，我们开始吧。","reply_language":"zh","face":"smile","motion":[{"action":"stop","duration":0.0}]}
- Greeting ja: {"reply":"はい、始めましょう。","reply_language":"ja","face":"smile","motion":[{"action":"stop","duration":0.0}]}
- Greeting en: {"reply":"Good morning, I am ready.","reply_language":"en","face":"smile","motion":[{"action":"stop","duration":0.0}]}
- Comfort en: {"reply":"I am here with you.","reply_language":"en","face":"comforting","motion":[{"action":"stop","duration":0.0}]}
Language rules:
- Detect the language of User/ASR text.
- reply_language must equal expected_reply_language when expected_reply_language is zh, ja, or en.
- reply must be written in reply_language.
- If expected_reply_language is zh, use Simplified Chinese.
- If expected_reply_language is ja, use Japanese.
- If expected_reply_language is en, use English.
- Do not translate to English unless expected_reply_language is en.
"""


CSV_FIELDS = [
    "time",
    "request_id",
    "trace_id",
    "mode",
    "model",
    "text",
    "expected_reply_language",
    "reply_language",
    "context_session",
    "context_turns",
    "context_used_reason",
    "context_candidates",
    "image_bytes",
    "http_status",
    "text_source",
    "text_ms",
    "asr_ms",
    "camera_wait_ms",
    "vlm_latency_ms",
    "validation_latency_ms",
    "publish_ms",
    "total_ms",
    "accepted",
    "fallback_used",
    "fallback_reason",
    "published",
    "raw_output",
    "published_plan",
]


def elapsed_ms(start, end):
    if not start or not end:
        return 0
    return max(0, int((end - start) * 1000))


class VlmBehaviorClient(Node):
    def __init__(self):
        super().__init__("vlm_behavior_client_node")
        self.declare_parameter("request_topic", "/robot_ai/response_request")
        self.declare_parameter("status_topic", "/robot_ai/status")
        self.declare_parameter("behavior_plan_topic", "/robot_behavior/plan")
        self.declare_parameter("asr_text_topic", "/robot_asr/text")
        self.declare_parameter("asr_request_topic", "/robot_asr/request")
        self.declare_parameter("camera_topic", "/robot_camera/jpeg")
        self.declare_parameter("llama_base_url", "http://192.168.64.246:18081")
        self.declare_parameter("model", "qwen3vl2b")
        self.declare_parameter("timeout_sec", 45.0)
        self.declare_parameter("asr_timeout_sec", 12.0)
        self.declare_parameter("camera_wait_sec", 3.0)
        self.declare_parameter("default_asr_duration_sec", 5.0)
        self.declare_parameter("max_tokens", 512)
        self.declare_parameter("temperature", 0.1)
        self.declare_parameter("publish_plans", True)
        self.declare_parameter("log_dir", "/tmp/vlm_client_logs")
        self.declare_parameter("context_turn_limit", 3)
        self.declare_parameter("context_max_chars", 900)
        self.declare_parameter("context_max_age_sec", 300.0)

        self.request_topic = str(self.get_parameter("request_topic").value)
        self.status_topic = str(self.get_parameter("status_topic").value)
        self.behavior_plan_topic = str(self.get_parameter("behavior_plan_topic").value)
        self.asr_text_topic = str(self.get_parameter("asr_text_topic").value)
        self.asr_request_topic = str(self.get_parameter("asr_request_topic").value)
        self.camera_topic = str(self.get_parameter("camera_topic").value)
        self.llama_base_url = str(self.get_parameter("llama_base_url").value).rstrip("/")
        self.model = str(self.get_parameter("model").value)
        self.timeout_sec = float(self.get_parameter("timeout_sec").value)
        self.asr_timeout_sec = float(self.get_parameter("asr_timeout_sec").value)
        self.camera_wait_sec = float(self.get_parameter("camera_wait_sec").value)
        self.default_asr_duration_sec = float(self.get_parameter("default_asr_duration_sec").value)
        self.max_tokens = int(self.get_parameter("max_tokens").value)
        self.temperature = float(self.get_parameter("temperature").value)
        self.publish_plans = bool(self.get_parameter("publish_plans").value)
        self.log_dir = Path(str(self.get_parameter("log_dir").value))
        self.context_turn_limit = max(0, int(self.get_parameter("context_turn_limit").value))
        self.context_max_chars = max(0, int(self.get_parameter("context_max_chars").value))
        self.context_max_age_sec = max(0.0, float(self.get_parameter("context_max_age_sec").value))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.log_dir / "vlm_client.jsonl"
        self.csv_path = self.log_dir / "vlm_client.csv"

        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.plan_pub = self.create_publisher(String, self.behavior_plan_topic, 10)
        self.asr_request_pub = self.create_publisher(String, self.asr_request_topic, 10)
        self.create_subscription(String, self.request_topic, self.on_request, 10)
        self.create_subscription(String, self.asr_text_topic, self.on_asr_text, 10)
        self.create_subscription(CompressedImage, self.camera_topic, self.on_camera, 10)

        self._lock = threading.Lock()
        self._worker = None
        self._asr_text = ""
        self._asr_time = 0.0
        self._camera_frame = b""
        self._camera_time = 0.0
        self._request_counter = 0
        self._conversation_history = []

        self.get_logger().info(
            "VLM behavior client ready: "
            f"request={self.request_topic}, status={self.status_topic}, "
            f"plan={self.behavior_plan_topic}, llama={self.llama_base_url}, model={self.model}"
        )
        self.publish_status({"state": "idle", "model": self.model, "timings": {}})

    def on_asr_text(self, msg):
        with self._lock:
            self._asr_text = clean_asr_text(msg.data)
            self._asr_time = time.time()

    def on_camera(self, msg):
        data = bytes(msg.data)
        if not data:
            return
        with self._lock:
            self._camera_frame = data
            self._camera_time = time.time()

    def on_request(self, msg):
        received_time = time.time()
        received_mono = time.perf_counter()
        try:
            request_payload = json.loads(msg.data or "{}")
            if not isinstance(request_payload, dict):
                raise ValueError("request root must be object")
        except Exception as exc:
            request_payload = {
                "request_id": self.next_request_id("bad_request"),
                "source": "parse_error",
                "mode": "run",
                "text": "",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }

        request_payload.setdefault("request_id", self.next_request_id("vlm"))
        request_payload.setdefault("trace_id", str(request_payload["request_id"]))
        request_payload.setdefault("mode", "run")
        request_payload.setdefault("source", "unknown")
        request_payload.setdefault("include_camera", True)
        request_payload.setdefault("include_asr", not bool(str(request_payload.get("text", "")).strip()))
        request_payload.setdefault("record", False)

        with self._lock:
            if self._worker and self._worker.is_alive():
                self.publish_status(
                    {
                        "state": "busy",
                        "request_id": request_payload["request_id"],
                        "trace_id": request_payload["trace_id"],
                        "mode": request_payload.get("mode", "run"),
                    },
                    received_time=received_time,
                    received_mono=received_mono,
                )
                return
            self._worker = threading.Thread(
                target=self.handle_request,
                args=(request_payload, received_time, received_mono),
                daemon=True,
            )
            self._worker.start()

    def handle_request(self, request_payload, received_time, received_mono):
        stamps = {"received": received_mono}
        wall_stamps = {"received": received_time}
        request_id = str(request_payload.get("request_id") or self.next_request_id("vlm"))
        trace_id = str(request_payload.get("trace_id") or request_id)
        mode = str(request_payload.get("mode", "run"))
        context_session = self.context_session_key(request_payload)
        self.publish_status(
            {
                "state": "received",
                "request_id": request_id,
                "trace_id": trace_id,
                "mode": mode,
                "model": self.model,
                "source": request_payload.get("source", ""),
                "context_session": context_session,
                "timings": self.make_timings(stamps),
            },
            received_time=received_time,
            received_mono=received_mono,
        )

        text = self.resolve_text(
            request_payload,
            trace_id,
            stamps,
            wall_stamps,
            received_time,
            received_mono,
        )
        if not text:
            text = "Please observe the latest camera frame and respond safely."
        expected_reply_language = detect_text_language(text, default="unknown")
        asr_quality_plan = make_asr_quality_guard_plan(
            text,
            trace_id,
            stamps.get("text_source", ""),
            request_payload.get("language", "auto"),
        )
        if asr_quality_plan:
            expected_reply_language = asr_quality_plan["reply_language"]
        image_bytes = b""
        if not asr_quality_plan:
            image_bytes = self.resolve_image(
                request_payload,
                after_time=received_time,
                stamps=stamps,
                wall_stamps=wall_stamps,
            )
        context_turns, context_info = self.get_context_turns(
            request_payload,
            text=text,
            expected_reply_language=expected_reply_language,
        )
        if asr_quality_plan:
            context_turns = []
            context_info = {"reason": "asr_quality_guard", "candidates": 0}

        raw_output = ""
        http_status = 0
        vlm_latency_ms = 0
        validation_latency_ms = 0
        decision = fallback_decision(
            "vlm: request not completed",
            raw_plan=None,
            expected_reply_language=expected_reply_language,
        )
        error = ""
        try:
            stamps["vlm_start"] = time.perf_counter()
            wall_stamps["vlm_start"] = time.time()
            if asr_quality_plan:
                stamps["vlm_end"] = time.perf_counter()
                wall_stamps["vlm_end"] = time.time()
                raw_output = json.dumps(
                    asr_quality_plan,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                http_status = 0
            else:
                self.publish_status(
                    {
                        "state": "vlm_request",
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "mode": mode,
                        "model": self.model,
                        "text": text[-200:],
                        "expected_reply_language": expected_reply_language,
                        "context_session": context_session,
                        "context_turns": len(context_turns),
                        "context_used_reason": context_info["reason"],
                        "context_candidates": context_info["candidates"],
                        "image_bytes": len(image_bytes),
                        "timings": self.make_timings(stamps),
                    },
                    received_time=received_time,
                    received_mono=received_mono,
                )
                context_policy_plan = make_context_policy_plan(
                    text,
                    trace_id,
                    expected_reply_language,
                    context_turns,
                )
                if context_policy_plan:
                    stamps["vlm_end"] = time.perf_counter()
                    wall_stamps["vlm_end"] = time.time()
                    raw_output = json.dumps(
                        context_policy_plan,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    http_status = 0
                else:
                    response = self.call_llama(text, image_bytes, trace_id, expected_reply_language, context_turns)
                    stamps["vlm_end"] = time.perf_counter()
                    wall_stamps["vlm_end"] = time.time()
                    raw_output = extract_model_text(response)
                    http_status = 200
            vlm_latency_ms = int((stamps["vlm_end"] - stamps["vlm_start"]) * 1000)

            json_text = extract_json_object(raw_output)
            policy_plan = make_policy_override_plan(text, trace_id, expected_reply_language)
            if policy_plan and not asr_quality_plan and not context_policy_plan:
                json_text = json.dumps(
                    policy_plan,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            stamps["validation_start"] = time.perf_counter()
            wall_stamps["validation_start"] = time.time()
            decision = decide_behavior_plan(
                json_text,
                expected_reply_language=expected_reply_language,
            )
            decision = repair_text_reading_language_mismatch(
                decision,
                text,
                expected_reply_language,
            )
            stamps["validation_end"] = time.perf_counter()
            wall_stamps["validation_end"] = time.time()
            validation_latency_ms = int((stamps["validation_end"] - stamps["validation_start"]) * 1000)
            if should_force_stop_only(text):
                decision.plan["motion"] = [{"action": "stop", "duration": 0.0}]
                decision.plan["motion_override"] = "stop_only_question"
                if is_stop_cancel_request(text):
                    apply_stop_cancel_reply(decision.plan, expected_reply_language)
            apply_visual_reply_quality_guard(decision.plan, text, expected_reply_language)
            apply_expression_style_guard(decision.plan, text)
            decision.plan["execution_mode"] = "dry_run" if mode == "dry_run" else "run"
            self.attach_trace(decision.plan, trace_id)
            state = "validated" if decision.accepted else "fallback"
            self.publish_status(
                {
                    **decision.to_status(state),
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "mode": mode,
                    "model": self.model,
                    "expected_reply_language": expected_reply_language,
                    "reply_language": decision.plan.get("reply_language", ""),
                    "context_session": context_session,
                    "context_turns": len(context_turns),
                    "context_used_reason": context_info["reason"],
                    "context_candidates": context_info["candidates"],
                    "vlm_latency_ms": vlm_latency_ms,
                    "validation_latency_ms": validation_latency_ms,
                    "image_bytes": len(image_bytes),
                    "timings": self.make_timings(stamps),
                },
                received_time=received_time,
                received_mono=received_mono,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            stamps.setdefault("vlm_end", time.perf_counter())
            wall_stamps.setdefault("vlm_end", time.time())
            vlm_latency_ms = int((stamps["vlm_end"] - stamps.get("vlm_start", received_mono)) * 1000)
            decision = fallback_decision(
                f"vlm: {error}",
                raw_plan=None,
                expected_reply_language=expected_reply_language,
            )
            decision.plan["execution_mode"] = "dry_run" if mode == "dry_run" else "run"
            self.attach_trace(decision.plan, trace_id)
            self.publish_status(
                {
                    **decision.to_status("fallback"),
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "mode": mode,
                    "model": self.model,
                    "expected_reply_language": expected_reply_language,
                    "reply_language": decision.plan.get("reply_language", ""),
                    "context_session": context_session,
                    "context_turns": len(context_turns),
                    "context_used_reason": context_info["reason"],
                    "context_candidates": context_info["candidates"],
                    "error": error,
                    "vlm_latency_ms": vlm_latency_ms,
                    "image_bytes": len(image_bytes),
                    "timings": self.make_timings(stamps),
                },
                received_time=received_time,
                received_mono=received_mono,
            )

        plan_payload = json.dumps(decision.plan, ensure_ascii=False, separators=(",", ":"))
        published = False
        if self.publish_plans:
            msg = String()
            msg.data = plan_payload
            self.plan_pub.publish(msg)
            published = True
            stamps["published"] = time.perf_counter()
            wall_stamps["published"] = time.time()
            self.publish_status(
                {
                    **decision.to_status("published"),
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "mode": mode,
                    "model": self.model,
                    "topic": self.behavior_plan_topic,
                    "expected_reply_language": expected_reply_language,
                    "reply_language": decision.plan.get("reply_language", ""),
                    "context_session": context_session,
                    "context_turns": len(context_turns),
                    "context_used_reason": context_info["reason"],
                    "context_candidates": context_info["candidates"],
                    "image_bytes": len(image_bytes),
                    "timings": self.make_timings(stamps),
                },
                received_time=received_time,
                received_mono=received_mono,
            )

        timings = self.make_timings(stamps)
        log_record = {
            "time": time.time(),
            "request_id": request_id,
            "trace_id": trace_id,
            "mode": mode,
            "model": self.model,
            "source": request_payload.get("source", ""),
            "text": text,
            "expected_reply_language": expected_reply_language,
            "reply_language": decision.plan.get("reply_language", ""),
            "context_session": context_session,
            "context_turns": len(context_turns),
            "context_used_reason": context_info["reason"],
            "context_candidates": context_info["candidates"],
            "context": context_turns,
            "image_bytes": len(image_bytes),
            "http_status": http_status,
            "vlm_latency_ms": vlm_latency_ms,
            "validation_latency_ms": validation_latency_ms,
            "text_source": timings.get("text_source", ""),
            "text_ms": timings.get("text_ms", 0),
            "asr_ms": timings.get("asr_ms", 0),
            "camera_wait_ms": timings.get("camera_wait_ms", 0),
            "publish_ms": timings.get("publish_ms", 0),
            "total_ms": timings.get("total_ms", 0),
            "accepted": decision.accepted,
            "fallback_used": decision.fallback_used,
            "fallback_reason": decision.fallback_reason,
            "errors": decision.errors,
            "raw_output": raw_output,
            "raw_plan": decision.raw_plan,
            "published": published,
            "published_plan": decision.plan,
            "error": error,
            "stamps": stamps,
            "wall_stamps": wall_stamps,
            "timings": timings,
        }
        self.write_logs(log_record)
        self.remember_turn(request_id, trace_id, request_payload, text, decision.plan, timings, published)

    def resolve_text(self, request_payload, request_id, stamps, wall_stamps, received_time, received_mono):
        explicit_text = clean_asr_text(str(request_payload.get("text", "") or ""))
        if explicit_text:
            stamps["text_ready"] = time.perf_counter()
            wall_stamps["text_ready"] = time.time()
            stamps["text_source"] = "explicit"
            return explicit_text

        include_asr = bool(request_payload.get("include_asr", True))
        record = bool(request_payload.get("record", False))
        if include_asr and record:
            with self._lock:
                self._asr_text = ""
                self._asr_time = 0.0
            duration = request_payload.get("duration", self.default_asr_duration_sec)
            try:
                duration = max(1.0, min(float(duration), 10.0))
            except Exception:
                duration = self.default_asr_duration_sec
            self.publish_status(
                {
                    "state": "asr_request",
                    "request_id": request_id,
                    "duration": duration,
                },
                received_time=received_time,
                received_mono=received_mono,
            )
            req = String()
            req.data = json.dumps(
                {"duration": duration, "language": request_payload.get("language", "auto")},
                separators=(",", ":"),
            )
            asr_start = time.time()
            stamps["asr_request"] = time.perf_counter()
            wall_stamps["asr_request"] = asr_start
            self.asr_request_pub.publish(req)
            text = self.wait_for_asr_text(after_time=asr_start)
            if text:
                stamps["asr_text"] = time.perf_counter()
                wall_stamps["asr_text"] = time.time()
                stamps["text_source"] = "asr_record"
                return text
            stamps["asr_timeout"] = time.perf_counter()
            wall_stamps["asr_timeout"] = time.time()
            stamps["text_source"] = "asr_timeout"
            return ""

        if include_asr:
            with self._lock:
                text = self._asr_text
            if text:
                stamps["asr_text_cached"] = time.perf_counter()
                wall_stamps["asr_text_cached"] = time.time()
                stamps["text_source"] = "asr_cached"
                return text
        stamps["text_source"] = "fallback_prompt"
        return ""

    def wait_for_asr_text(self, after_time):
        deadline = time.monotonic() + self.asr_timeout_sec
        while time.monotonic() < deadline:
            with self._lock:
                text = self._asr_text
                text_time = self._asr_time
            if text and text_time >= after_time:
                return text
            time.sleep(0.1)
        return ""

    def resolve_image(self, request_payload, after_time=0.0, stamps=None, wall_stamps=None):
        if not bool(request_payload.get("include_camera", True)):
            if stamps is not None:
                stamps["camera_skipped"] = time.perf_counter()
            if wall_stamps is not None:
                wall_stamps["camera_skipped"] = time.time()
            return b""
        if stamps is not None:
            stamps["camera_wait_start"] = time.perf_counter()
        if wall_stamps is not None:
            wall_stamps["camera_wait_start"] = time.time()
        deadline = time.monotonic() + max(0.0, self.camera_wait_sec)
        while True:
            with self._lock:
                frame = self._camera_frame
                frame_time = self._camera_time
            if frame and frame_time >= after_time:
                if stamps is not None:
                    stamps["camera_ready"] = time.perf_counter()
                    stamps["camera_frame_time"] = frame_time
                if wall_stamps is not None:
                    wall_stamps["camera_ready"] = time.time()
                    wall_stamps["camera_frame_time"] = frame_time
                return frame
            if frame and self.camera_wait_sec <= 0:
                if stamps is not None:
                    stamps["camera_ready"] = time.perf_counter()
                    stamps["camera_frame_time"] = frame_time
                if wall_stamps is not None:
                    wall_stamps["camera_ready"] = time.time()
                    wall_stamps["camera_frame_time"] = frame_time
                return frame
            if time.monotonic() >= deadline:
                if stamps is not None:
                    stamps["camera_ready"] = time.perf_counter()
                    stamps["camera_frame_time"] = frame_time
                if wall_stamps is not None:
                    wall_stamps["camera_ready"] = time.time()
                    wall_stamps["camera_frame_time"] = frame_time
                return frame
            time.sleep(0.05)

    def make_timings(self, stamps, now=None):
        now = now or time.perf_counter()
        received = stamps.get("received", now)
        timings = {
            "total_ms": elapsed_ms(received, now),
            "text_source": stamps.get("text_source", ""),
            "asr_ms": elapsed_ms(stamps.get("asr_request"), stamps.get("asr_text")),
            "camera_wait_ms": elapsed_ms(stamps.get("camera_wait_start"), stamps.get("camera_ready")),
            "vlm_ms": elapsed_ms(stamps.get("vlm_start"), stamps.get("vlm_end")),
            "validation_ms": elapsed_ms(stamps.get("validation_start"), stamps.get("validation_end")),
            "publish_ms": elapsed_ms(stamps.get("validation_end"), stamps.get("published")),
        }
        if stamps.get("text_ready"):
            timings["text_ms"] = elapsed_ms(received, stamps.get("text_ready"))
        if stamps.get("asr_text_cached"):
            timings["text_ms"] = elapsed_ms(received, stamps.get("asr_text_cached"))
        if stamps.get("asr_text"):
            timings["text_ms"] = elapsed_ms(received, stamps.get("asr_text"))
        return timings

    def attach_trace(self, plan, trace_id):
        plan["input_id"] = trace_id
        plan["trace_id"] = trace_id

    def context_session_key(self, request_payload):
        session = str(request_payload.get("context_session", "") or "").strip()
        if session:
            return session
        source = str(request_payload.get("source", "unknown") or "unknown")
        mode = str(request_payload.get("mode", "run") or "run")
        return f"{source}:{mode}"

    def get_context_turns(self, request_payload, text="", expected_reply_language="unknown"):
        context_info = {"reason": "disabled", "candidates": 0}
        if not self.context_turn_limit or not self.context_max_chars:
            return [], context_info
        now = time.time()
        session = self.context_session_key(request_payload)
        with self._lock:
            history = list(self._conversation_history)
        history = [item for item in history if item.get("session") == session]
        if self.context_max_age_sec:
            history = [
                item
                for item in history
                if now - float(item.get("time", 0.0) or 0.0) <= self.context_max_age_sec
            ]
        candidates = len(history)
        reason = context_relevance_reason(text, request_payload)
        context_info = {"reason": reason or "fresh_request", "candidates": candidates}
        if not reason:
            return [], context_info

        if reason != "forced" and not allow_cross_language_context(text):
            before_language_filter = len(history)
            history = [
                item
                for item in history
                if context_turn_matches_language(item, expected_reply_language)
            ]
            if before_language_filter and not history:
                context_info["reason"] = f"{reason}:no_same_language_context"
                return [], context_info

        selected = trim_context_turns(history[-self.context_turn_limit :], self.context_max_chars)
        if not selected and candidates:
            context_info["reason"] = f"{reason}:no_context_selected"
        return selected, context_info

    def remember_turn(self, request_id, trace_id, request_payload, text, plan, timings, published):
        if not self.context_turn_limit:
            return
        if not published or plan.get("source") != "vlm" or plan.get("fallback_used"):
            return
        reply = str(plan.get("reply", "") or "").strip()
        user_text = str(text or "").strip()
        if not user_text and not reply:
            return
        turn = {
            "time": time.time(),
            "session": self.context_session_key(request_payload),
            "request_id": request_id,
            "trace_id": trace_id,
            "source": request_payload.get("source", ""),
            "mode": request_payload.get("mode", "run"),
            "user": user_text[:400],
            "assistant": reply[:400],
            "reply_language": plan.get("reply_language", ""),
            "plan_source": plan.get("source", ""),
            "motion": [item.get("action", "") for item in plan.get("motion", []) if isinstance(item, dict)],
            "policy_override": plan.get("policy_override", ""),
            "fallback_reason": plan.get("fallback_reason", ""),
            "face": plan.get("face", ""),
            "published": bool(published),
            "total_ms": timings.get("total_ms", 0),
        }
        with self._lock:
            self._conversation_history.append(turn)
            self._conversation_history = self._conversation_history[-max(1, self.context_turn_limit * 3) :]

    def call_llama(self, text, image_bytes, trace_id, expected_reply_language, context_turns=None):
        context_text = format_context_turns(context_turns or [])
        user_content = [
            {
                "type": "text",
                "text": (
                    f"input_id: {trace_id}\n"
                    f"trace_id: {trace_id}\n"
                    f"expected_reply_language: {expected_reply_language}\n"
                    f"{context_text}"
                    f"User/ASR text: {text}\n"
                    "Use the latest image if provided. Keep reply short and do not guess uncertain visual details.\n"
                    "For visual questions or text-reading, answer from the latest image, not from old context.\n"
                    "If the user asks about what was just asked, previous answers, or recent progress, answer from Recent context directly.\n"
                    "Do not repeat old motion unless the current user asks.\n"
                    "Output contract checklist before you answer:\n"
                    f"- input_id must be exactly {trace_id}\n"
                    "- source must be \"vlm\"\n"
                    "- validated must be true\n"
                    "- fallback_used must be false\n"
                    "- include reply, reply_language, emotion, tts_style, face, and motion\n"
                    "- final motion must be stop\n"
                    "- do not omit required keys even for OCR or one-word answers\n"
                    "Produce the behavior plan JSON now."
                ),
            }
        ]
        if image_bytes:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                }
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.llama_base_url}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[-1000:]
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc

    def write_logs(self, record):
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

        csv_exists = self.csv_path.exists()
        with self.csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            if not csv_exists:
                writer.writeheader()
            row = {}
            for field in CSV_FIELDS:
                value = record.get(field, "")
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                row[field] = value
            writer.writerow(row)

    def publish_status(self, payload, received_time=None, received_mono=None):
        status = dict(payload)
        status["time"] = time.time()
        if received_time is not None:
            status["received_time"] = received_time
            if received_mono is not None:
                status["latency_ms"] = int((time.perf_counter() - received_mono) * 1000)
            else:
                status["latency_ms"] = int((time.time() - received_time) * 1000)
        msg = String()
        msg.data = json.dumps(status, ensure_ascii=False, separators=(",", ":"))
        self.status_pub.publish(msg)
        if status.get("state") in {"fallback", "error", "busy"}:
            self.get_logger().warn(msg.data)
        else:
            self.get_logger().info(msg.data)

    def next_request_id(self, prefix):
        self._request_counter += 1
        return f"{prefix}_{int(time.time() * 1000)}_{self._request_counter}"


def clean_asr_text(text):
    value = str(text or "")
    while "<|" in value and "|>" in value:
        start = value.find("<|")
        end = value.find("|>", start)
        if end < start:
            break
        value = value[:start] + value[end + 2 :]
    return value.strip()


def payload_bool(payload, key, default=False):
    value = payload.get(key, default) if isinstance(payload, dict) else default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def context_relevance_reason(text, request_payload):
    mode = str(request_payload.get("context_mode", "") or "").strip().lower()
    if mode in {"off", "none", "false", "0", "disabled"}:
        return ""
    if mode in {"force", "on", "always"} or payload_bool(request_payload, "force_context", False):
        return "forced"
    if is_translation_or_language_switch(text):
        return "translation_or_language_switch"
    if is_correction_request(text):
        return "correction"
    if is_repeat_request(text):
        return "repeat"
    if is_meta_context_request(text):
        return "meta_context"
    if is_text_reading_request(text) or is_visual_question_request(text):
        return ""
    if is_followup_reference(text):
        return "followup_reference"
    return ""


def has_any_pattern(text, patterns):
    value = str(text or "")
    lower = value.lower()
    return any(pattern.lower() in lower for pattern in patterns)


def is_translation_or_language_switch(text):
    return has_any_pattern(
        text,
        (
            "translate",
            "translation",
            "in english",
            "in japanese",
            "in chinese",
            "say it in",
            "英語で",
            "日本語で",
            "中国語で",
            "中文",
            "日文",
            "英文",
            "翻译",
            "翻譯",
            "翻訳",
            "訳して",
        ),
    )


def is_correction_request(text):
    return has_any_pattern(
        text,
        (
            "不是",
            "不对",
            "不對",
            "纠正",
            "糾正",
            "改成",
            "其实",
            "其實",
            "違う",
            "ではなく",
            "じゃなく",
            "actually",
            "correction",
            "not that",
            "not a",
            "not the",
        ),
    )


def is_repeat_request(text):
    return has_any_pattern(
        text,
        (
            "再说一遍",
            "再說一遍",
            "重复",
            "重複",
            "もう一度",
            "繰り返",
            "repeat",
            "say that again",
            "again",
        ),
    )


def is_followup_reference(text):
    return has_any_pattern(
        text,
        (
            "刚才",
            "剛才",
            "上一个",
            "上一個",
            "前一个",
            "前一個",
            "之前",
            "那个",
            "那個",
            "那件",
            "它",
            "继续",
            "繼續",
            "接着",
            "接著",
            "さっき",
            "先ほど",
            "前の",
            "それ",
            "あれ",
            "続け",
            "previous",
            "earlier",
            "last one",
            "that one",
            "that",
            " it",
            "continue",
        ),
    )


def is_meta_context_request(text):
    return has_any_pattern(
        text,
        (
            "刚才问",
            "刚才我问",
            "刚才的问题",
            "刚才那个问题",
            "刚才说",
            "刚才回答",
            "刚才做",
            "刚才执行",
            "刚才我让你",
            "刚才你看",
            "我们刚才",
            "上一轮",
            "上一步",
            "前面",
            "之前的",
            "当前进度",
            "现在进度",
            "做到哪",
            "做到哪一步",
            "完成到哪",
            "进展",
            "总结一下",
            "回顾一下",
            "刚才测试",
            "分别是什么",
            "分別是什麼",
            "两件东西",
            "兩件東西",
            "两个东西",
            "两个分别",
            "さっき聞",
            "さっきの質問",
            "さっき何",
            "前回",
            "進捗",
            "どこまで",
            "what did i ask",
            "what did you say",
            "what did we just",
            "where are we",
            "current progress",
            "what is the progress",
            "what did we do",
            "summarize what happened",
            "what were they",
            "two things",
        ),
    )


def allow_cross_language_context(text):
    return is_translation_or_language_switch(text) or is_meta_context_request(text)


def context_turn_matches_language(turn, expected_reply_language):
    expected = str(expected_reply_language or "unknown")
    if expected not in {"zh", "ja", "en"}:
        return True
    if str(turn.get("reply_language", "")) == expected:
        return True
    user_text = str(turn.get("user", "") or "")
    return detect_text_language(user_text, default="unknown") == expected


def extract_model_text(response):
    choices = response.get("choices", []) if isinstance(response, dict) else []
    if choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content", "")
                if isinstance(content, str):
                    return content.strip()
                if isinstance(content, list):
                    chunks = []
                    for item in content:
                        if isinstance(item, dict) and isinstance(item.get("text"), str):
                            chunks.append(item["text"])
                    return "\n".join(chunks).strip()
            if isinstance(first.get("text"), str):
                return first["text"].strip()
    if isinstance(response, dict) and isinstance(response.get("content"), str):
        return response["content"].strip()
    return json.dumps(response, ensure_ascii=False)


def trim_text(value, max_chars):
    text = " ".join(str(value or "").split())
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def trim_context_turns(turns, max_chars):
    budget = max(0, int(max_chars))
    if not turns or not budget:
        return []
    result = []
    for turn in reversed(list(turns)):
        user = trim_text(turn.get("user", ""), 180)
        assistant = trim_text(turn.get("assistant", ""), 180)
        if not user and not assistant:
            continue
        item = {
            "trace_id": str(turn.get("trace_id", "")),
            "user": user,
            "assistant": assistant,
            "reply_language": str(turn.get("reply_language", "")),
            "source": str(turn.get("source", "")),
            "policy_override": str(turn.get("policy_override", "")),
            "motion": list(turn.get("motion", []))[:3],
        }
        cost = len(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
        if result and cost > budget:
            break
        if cost > budget:
            item["user"] = trim_text(item["user"], max(0, budget // 2))
            item["assistant"] = trim_text(item["assistant"], max(0, budget // 2))
        result.append(item)
        budget -= min(cost, budget)
    return list(reversed(result))


def format_context_turns(turns):
    if not turns:
        return "Recent context: none\n"
    lines = [
        "Recent context:",
        "Use this only for resolving references; current User/ASR text has priority.",
        "For questions about previous turns or progress, summarize these turns directly.",
    ]
    for index, turn in enumerate(turns, start=1):
        user = turn.get("user", "")
        assistant = turn.get("assistant", "")
        motion = ",".join(turn.get("motion", []) or [])
        policy_override = turn.get("policy_override", "")
        lines.append(f"{index}. user: {user}")
        lines.append(f"   assistant: {assistant}")
        if motion:
            lines.append(f"   motion: {motion}")
        if policy_override:
            lines.append(f"   policy_override: {policy_override}")
    return "\n".join(lines) + "\n"


def extract_json_object(text):
    value = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        value = fence.group(1).strip()
    if value.startswith("{") and value.endswith("}"):
        return value

    start = value.find("{")
    if start < 0:
        raise ValueError("model output did not contain a JSON object")
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(value)):
        char = value[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return value[start : index + 1]
    raise ValueError("model output JSON object was not balanced")


def is_live_external_fact_question(text):
    value = str(text or "").lower()
    topic_patterns = (
        "天气",
        "天氣",
        "气温",
        "氣溫",
        "新闻",
        "新聞",
        "最新消息",
        "即時",
        "日程",
        "安排",
        "价格",
        "價格",
        "股价",
        "股價",
        "天気",
        "weather",
        "ニュース",
        "news",
        "予定",
        "schedule",
        "価格",
        "株価",
        "price",
        "current event",
        "current events",
        "latest news",
    )
    live_modifiers = (
        "实时",
        "即時",
        "最新",
        "今天",
        "明天",
        "现在",
        "現在",
        "current",
        "latest",
        "today",
        "tomorrow",
        "now",
    )
    if any(pattern in value for pattern in topic_patterns):
        return True
    return any(pattern in value for pattern in live_modifiers) and any(
        pattern in value
        for pattern in (
            "东京",
            "東京",
            "tokyo",
            "新闻",
            "ニュース",
            "news",
            "天气",
            "天気",
            "weather",
        )
    )


def is_physical_ability_request(text):
    value = str(text or "").lower()
    patterns = (
        "pick up",
        "pickup",
        "grab",
        "grasp",
        "hold this",
        "hold the",
        "carry",
        "bring me",
        "press the",
        "open the",
        "close the",
        "拿起来",
        "拿起來",
        "拿一下",
        "帮我拿",
        "幫我拿",
        "抓起来",
        "抓起來",
        "抓一下",
        "捡起来",
        "撿起來",
        "抱起来",
        "抱起來",
        "递给我",
        "遞給我",
        "押して",
        "開けて",
        "閉めて",
        "持って",
        "取って",
        "拾って",
        "つかんで",
        "運んで",
    )
    return any(pattern in value for pattern in patterns)


def is_uncertain_text_reading_request(text):
    value = str(text or "").lower()
    read_patterns = (
        "read",
        "文字",
        "テキスト",
        "読ん",
        "読み",
        "读",
        "讀",
        "念",
        "ocr",
    )
    uncertainty_patterns = (
        "tiny",
        "small",
        "unclear",
        "distant",
        "far",
        "blurry",
        "很小",
        "小字",
        "模糊",
        "看不清",
        "远处",
        "遠處",
        "細かい",
        "小さい",
        "見えにくい",
        "ぼやけ",
    )
    finger_patterns = ("手指", "指", "finger")
    if any(pattern in value for pattern in read_patterns) and any(
        pattern in value for pattern in uncertainty_patterns
    ):
        return True
    return any(pattern in value for pattern in read_patterns) and any(
        pattern in value for pattern in finger_patterns
    )


def is_greeting_request(text):
    value = str(text or "").lower()
    greeting_patterns = (
        "good morning",
        "good afternoon",
        "good evening",
        "let's get started",
        "lets get started",
        "get started",
        "早上好",
        "上午好",
        "下午好",
        "晚上好",
        "开始吧",
        "開始吧",
        "おはよう",
        "こんにちは",
        "こんばんは",
        "始めよう",
        "始めましょう",
    )
    return any(pattern in value for pattern in greeting_patterns)


def is_comfort_request(text):
    value = str(text or "").lower()
    patterns = (
        "comfort me",
        "encourage me",
        "cheer me up",
        "i am nervous",
        "i'm nervous",
        "i feel nervous",
        "i am worried",
        "i'm worried",
        "i feel worried",
        "i am scared",
        "i'm scared",
        "i feel scared",
        "a little nervous",
        "有点紧张",
        "有點緊張",
        "有些紧张",
        "有些緊張",
        "我紧张",
        "我緊張",
        "我害怕",
        "担心",
        "擔心",
        "安慰",
        "鼓励",
        "鼓勵",
        "緊張",
        "不安",
        "怖い",
        "励まし",
        "励まして",
        "慰め",
        "安心",
    )
    return any(pattern in value for pattern in patterns)


def is_positive_reaction_request(text):
    value = str(text or "").lower()
    patterns = (
        "good job",
        "well done",
        "great",
        "nice",
        "thank you",
        "thanks",
        "做得好",
        "很好",
        "不错",
        "不錯",
        "ありがとう",
        "よくでき",
        "すごい",
    )
    return any(pattern in value for pattern in patterns)


def is_surprise_request(text):
    value = str(text or "").lower()
    patterns = (
        "surprise",
        "surprised",
        "wow",
        "amazing",
        "びっくり",
        "驚",
        "すごい",
        "惊讶",
        "驚訝",
        "吃惊",
        "吃驚",
        "哇",
    )
    return any(pattern in value for pattern in patterns)


def is_stop_cancel_request(text):
    value = str(text or "").lower()
    stay_still_only_patterns = (
        "stay still",
        "please stay still",
        "do not move",
        "don't move",
        "待在原地",
        "留在原地",
        "不要移动",
        "请不要移动",
        "止まっていて",
        "動かないで",
    )
    if is_greeting_request(value) and any(pattern in value for pattern in stay_still_only_patterns):
        return False
    cancel_patterns = (
        "cancel",
        "interrupt",
        "never mind",
        "取消",
        "中止",
        "やめて",
        "キャンセル",
    )
    if any(pattern in value for pattern in cancel_patterns):
        return True
    motion_words = (
        "move",
        "forward",
        "backward",
        "look around",
        "turn",
        "向前",
        "前进",
        "前進",
        "后退",
        "後退",
        "移动",
        "移動",
        "周围",
        "周囲",
        "周り",
        "move_forward",
        "move_backward",
    )
    stop_only_patterns = (
        "stop",
        "please stop",
        "停止",
        "停下",
        "停住",
        "别动",
        "不要动",
        "止まって",
    )
    if any(pattern in value for pattern in stop_only_patterns):
        return not any(pattern in value for pattern in motion_words)
    return False


def is_japanese_look_around_request(text):
    value = str(text or "").lower()
    if any(pattern in value for pattern in ("動かない", "動かないで", "止まっていて")):
        return False
    look_patterns = ("周り", "まわり", "見回", "見てから", "見る")
    stop_patterns = ("止ま", "停止", "ください")
    return any(pattern in value for pattern in look_patterns) and any(
        pattern in value for pattern in stop_patterns
    )


def normalize_reply_language(language):
    return language if language in {"zh", "ja", "en"} else "ja"


def normalize_asr_feedback_language(language_hint, text=""):
    detected = detect_text_language(text, default="unknown")
    if detected in {"zh", "ja", "en"}:
        return detected
    hint = str(language_hint or "").strip().lower()
    if hint.startswith(("zh", "cmn", "yue")) or hint in {"chinese", "cn"}:
        return "zh"
    if hint.startswith("ja") or hint in {"japanese", "jp"}:
        return "ja"
    if hint.startswith("en") or hint in {"english", "us", "uk"}:
        return "en"
    return "zh"


def is_low_quality_asr_text(text):
    value = clean_asr_text(text)
    if not value:
        return True
    compact = re.sub(r"\s+", "", value)
    if not compact:
        return True
    content = re.sub(r"[\W_]+", "", compact, flags=re.UNICODE)
    if not content:
        return True
    if len(content) <= 1:
        if content.isascii():
            return True
        if detect_text_language(value, default="unknown") == "unknown":
            return True
    filler = content.lower()
    low_information_fillers = {
        "yeah",
        "yes",
        "yep",
        "ok",
        "okay",
        "sure",
        "uh",
        "um",
        "嗯",
        "啊",
        "呃",
        "はい",
        "うん",
        "ええ",
    }
    if filler in low_information_fillers:
        return True
    return False


def make_asr_quality_guard_plan(text, trace_id, text_source, language_hint="auto"):
    source = str(text_source or "")
    if source == "asr_timeout":
        policy_override = "asr_timeout"
    elif source in {"asr_record", "asr_cached"} and is_low_quality_asr_text(text):
        policy_override = "asr_low_quality_text"
    else:
        return None

    language = normalize_asr_feedback_language(language_hint, text)
    return make_policy_guard_plan(
        trace_id,
        language,
        policy_override,
        {
            "zh": "我没听清，请再说一遍。",
            "ja": "よく聞き取れませんでした。もう一度お願いします。",
            "en": "I did not hear that clearly. Please say it again.",
        },
        face="thinking",
        emotion="neutral",
        tts_style="calm",
    )


def make_policy_guard_plan(
    trace_id,
    language,
    policy_override,
    replies,
    face="thinking",
    emotion="neutral",
    tts_style="calm",
):
    normalized = normalize_reply_language(language)
    return {
        "input_id": trace_id,
        "trace_id": trace_id,
        "source": "policy_guard",
        "validated": True,
        "fallback_used": False,
        "policy_override": policy_override,
        "reply": replies[normalized],
        "reply_language": normalized,
        "emotion": emotion,
        "tts_style": tts_style,
        "face": face,
        "motion": [{"action": "stop", "duration": 0.0}],
    }


def make_policy_motion_plan(trace_id, language, policy_override, replies, motion):
    plan = make_policy_guard_plan(trace_id, language, policy_override, replies, face="neutral")
    plan["motion"] = motion
    return plan


def make_context_policy_plan(text, trace_id, language, context_turns):
    if not is_meta_context_request(text) or not context_turns:
        return None
    normalized = normalize_reply_language(language)
    turns = [turn for turn in context_turns if turn.get("user") or turn.get("assistant")]
    if not turns:
        return None

    if is_recent_item_list_question(text):
        useful_answers = [
            trim_context_answer(turn.get("assistant", ""))
            for turn in turns
            if is_useful_context_answer(turn.get("assistant", ""))
        ]
        if useful_answers:
            if has_any_pattern(text, ("两", "兩", "二", "two", "2", "二つ")) and len(useful_answers) > 2:
                useful_answers = useful_answers[-2:]
            answer_text = "；".join(useful_answers)
            replies = {
                "zh": f"刚才我分别回答：{answer_text}。",
                "ja": f"さっき私は順に、{answer_text} と答えました。",
                "en": f"My recent answers were: {answer_text}.",
            }
            return make_policy_guard_plan(
                trace_id,
                normalized,
                "context_summary",
                replies,
                face="thinking",
            )

    last = turns[-1]
    user_text = trim_text(last.get("user", ""), 90)
    assistant_text = trim_context_answer(last.get("assistant", ""))
    if not assistant_text:
        assistant_text = "我没有留下可用回答"
    replies = {
        "zh": f"刚才你问：{user_text}。我回答：{assistant_text}。",
        "ja": f"さっきあなたは「{user_text}」と聞き、私は「{assistant_text}」と答えました。",
        "en": f"You just asked: {user_text}. I answered: {assistant_text}.",
    }
    return make_policy_guard_plan(
        trace_id,
        normalized,
        "context_summary",
        replies,
        face="thinking",
    )


def is_recent_item_list_question(text):
    return has_any_pattern(
        text,
        (
            "分别",
            "分別",
            "两件",
            "兩件",
            "两个",
            "兩個",
            "二つ",
            "what were they",
            "two things",
            "what are they",
        ),
    )


def trim_context_answer(value):
    return trim_text(value, 80).rstrip("。.")


def is_useful_context_answer(value):
    text = str(value or "").strip()
    if not text:
        return False
    uncertain_patterns = (
        "不确定",
        "不清楚",
        "看不清",
        "よく分かりません",
        "見えません",
        "not sure",
        "cannot tell",
        "cannot read",
        "unclear",
    )
    return not has_any_pattern(text, uncertain_patterns)


def make_policy_override_plan(text, trace_id, language):
    if is_greeting_request(text):
        return make_policy_guard_plan(
            trace_id,
            language,
            "greeting_stay_still",
            {
                "zh": "好的，我们开始吧。",
                "ja": "はい、始めましょう。",
                "en": "Good morning, I am ready.",
            },
            face="smile",
            emotion="happy",
            tts_style="cheerful",
        )
    if is_comfort_request(text):
        return make_policy_guard_plan(
            trace_id,
            language,
            "comforting_response",
            {
                "zh": "别担心，我在这里。",
                "ja": "大丈夫です。そばにいます。",
                "en": "I am here with you.",
            },
            face="comforting",
            emotion="comforting",
            tts_style="soft",
        )
    if is_stop_cancel_request(text):
        return make_policy_guard_plan(
            trace_id,
            language,
            "stop_cancel",
            {
                "zh": "好的，我会停止。",
                "ja": "はい、止まります。",
                "en": "Okay, I will stop.",
            },
            face="neutral",
        )
    if is_live_external_fact_question(text):
        return make_policy_guard_plan(
            trace_id,
            language,
            "live_external_fact",
            {
                "zh": "我这里无法确认实时信息。",
                "ja": "ここでは最新情報を確認できません。",
                "en": "I cannot check live information here.",
            },
        )
    if is_physical_ability_request(text):
        return make_policy_guard_plan(
            trace_id,
            language,
            "physical_ability_limit",
            {
                "zh": "我这里不能拿取物体。",
                "ja": "ここでは物を持てません。",
                "en": "I cannot pick up objects here.",
            },
            face="thinking",
        )
    if is_mixed_motion_visual_request(text):
        return make_policy_guard_plan(
            trace_id,
            language,
            "multi_stage_observation_limit",
            {
                "zh": "我现在不能移动后再观察回答。",
                "ja": "移動後に見て答えることはまだできません。",
                "en": "I cannot move first and then answer from a new view yet.",
            },
            face="thinking",
        )
    if is_japanese_look_around_request(text):
        return make_policy_motion_plan(
            trace_id,
            language,
            "deterministic_look_around",
            {
                "zh": "我会看看周围，然后停下。",
                "ja": "周りを見てから止まります。",
                "en": "I will look around, then stop.",
            },
            [{"action": "look_around", "duration": 1.0}, {"action": "stop", "duration": 0.0}],
        )
    deterministic_motion = make_deterministic_motion_sequence(text)
    if deterministic_motion:
        return make_policy_motion_plan(
            trace_id,
            language,
            "deterministic_motion_sequence",
            {
                "zh": "好的，按顺序移动后停下。",
                "ja": "順番に動いてから止まります。",
                "en": "Okay, moving in order, then stopping.",
            },
            deterministic_motion,
        )
    return None


def apply_stop_cancel_reply(plan, language):
    normalized = normalize_reply_language(language)
    replies = {
        "zh": "好的，我会停止。",
        "ja": "はい、止まります。",
        "en": "Okay, I will stop.",
    }
    plan["reply"] = replies[normalized]
    plan["reply_language"] = normalized
    plan["policy_override"] = "stop_cancel"


def is_text_reading_request(text):
    value = str(text or "").lower()
    patterns = (
        "read",
        "text",
        "文字",
        "包装",
        "ラベル",
        "テキスト",
        "読ん",
        "読み",
        "读",
        "讀",
        "念",
        "ocr",
    )
    return any(pattern in value for pattern in patterns)


def is_visual_question_request(text):
    value = str(text or "").lower()
    patterns = (
        "what is this",
        "what is it",
        "what am i holding",
        "what's in my hand",
        "what is in my hand",
        "what can you see",
        "what do you see",
        "latest camera frame",
        "latest camel frame",
        "camera frame",
        "camel frame",
        "look at the frame",
        "the frame",
        "image",
        "画像",
        "画面",
        "看图",
        "看圖",
        "我拿着什么",
        "我拿著什麼",
        "我手里",
        "我手裡",
        "这是什么",
        "是什么",
        "图",
        "圖",
        "看到什么",
        "看到了什么",
        "何を持",
        "手に持",
        "これは何ですか",
        "何ですか",
        "何んですか",
        "ご覧",
        "何が見え",
    )
    return any(pattern in value for pattern in patterns)


def make_deterministic_motion_sequence(text):
    value = str(text or "").lower()
    if not is_explicit_motion_request(value) or is_stop_cancel_request(value):
        return None
    token_specs = (
        (
            "move_forward_slow",
            r"move\s+forward|come\s+closer|\bforward\b|向前走|向前|前走|前进|前進|往前|靠近|近づ",
        ),
        (
            "move_backward",
            r"move\s+backward|go\s+back|backward|\bback\b|向后退|向後退|后退|後退|退回|往后|往後|後ろ",
        ),
        ("turn_left", r"turn\s+left|left\s+turn|向左转|向左轉|左转|左轉|左に|左へ|左回"),
        ("turn_right", r"turn\s+right|right\s+turn|向右转|向右轉|右转|右轉|右に|右へ|右回"),
    )
    matches = []
    for action, pattern in token_specs:
        for match in re.finditer(pattern, value, flags=re.IGNORECASE):
            matches.append((match.start(), action))
    matches.sort(key=lambda item: item[0])
    actions = []
    used_starts = set()
    for start, action in matches:
        if start in used_starts:
            continue
        used_starts.add(start)
        actions.append(action)
    actions = actions[:4]
    if not actions:
        return None
    motion = [{"action": action, "duration": 0.8} for action in actions]
    motion.append({"action": "stop", "duration": 0.0})
    return motion


def is_mixed_motion_visual_request(text):
    value = str(text or "").lower()
    if not is_explicit_motion_request(value):
        return False
    visual_after_motion_patterns = (
        "then tell me what you see",
        "tell me what you see",
        "what do you see after",
        "what can you see after",
        "然后告诉我",
        "然後告訴我",
        "再告诉我",
        "再告訴我",
        "你看到了什么",
        "你看見了什麼",
        "見えたもの",
        "見えたか",
        "何が見えた",
        "見て答",
    )
    return any(pattern in value for pattern in visual_after_motion_patterns)


def is_user_holding_question(text):
    value = str(text or "").lower()
    patterns = (
        "what am i holding",
        "what's in my hand",
        "what is in my hand",
        "what do i have in my hand",
        "what am i holding right now",
        "我拿着什么",
        "我拿著什麼",
        "我手里拿",
        "我手裡拿",
        "我手上",
        "何を持",
        "手に持",
    )
    return any(pattern in value for pattern in patterns)


def is_future_observation_placeholder(reply):
    value = str(reply or "").lower()
    patterns = (
        "i will observe",
        "i am observing",
        "i'm observing",
        "the robot is observing",
        "robot is observing",
        "observing the frame",
        "observing the current",
        "observing the latest",
        "i will look",
        "i am looking",
        "i'm looking",
        "the robot is looking",
        "i will check",
        "i am checking",
        "i'm checking",
        "i will read",
        "let me look",
        "我将观察",
        "我会观察",
        "我正在观察",
        "我将查看",
        "我会查看",
        "我正在查看",
        "我将仔细",
        "我会仔细",
        "确认します",
        "確認します",
        "読みます",
        "読んでください",
        "見てください",
        "画像を見てください",
        "画面を見てください",
        "見てみます",
        "見ます",
    )
    return any(pattern in value for pattern in patterns)


def is_visual_non_answer(reply):
    value = str(reply or "").strip().lower()
    patterns = (
        "i am here with you",
        "i'm here with you",
        "good morning",
        "let's get started",
        "i am ready",
        "the robot is stopping",
        "robot is stopping",
        "i am stopping",
        "i'm stopping",
        "はい、始めましょう",
        "ご注意ください",
        "注意してください",
        "動かないでください",
        "止まってください",
        "be careful",
        "please be careful",
        "好的，我们开始吧",
        "我在这里",
    )
    return any(pattern in value for pattern in patterns)


def apply_visual_reply_quality_guard(plan, text, language):
    if not isinstance(plan, dict):
        return
    if not (is_text_reading_request(text) or is_visual_question_request(text)):
        return
    plan["motion"] = [{"action": "stop", "duration": 0.0}]
    apply_user_perspective_guard(plan, text, language)
    apply_robot_holding_visual_guard(plan, text, language)
    if not (
        is_future_observation_placeholder(plan.get("reply", ""))
        or (is_visual_question_request(text) and is_visual_non_answer(plan.get("reply", "")))
    ):
        return
    normalized = normalize_reply_language(language)
    if is_text_reading_request(text):
        replies = {
            "zh": "这段文字我看不清。",
            "ja": "この文字はよく見えません。",
            "en": "I cannot read that clearly.",
        }
        override = "visual_reply_quality:text_unclear"
    else:
        replies = {
            "zh": "我不确定这是什么。",
            "ja": "これはよく分かりません。",
            "en": "I am not sure what it is.",
        }
        override = "visual_reply_quality:uncertain_object"
    plan["reply"] = replies[normalized]
    plan["reply_language"] = normalized
    plan["face"] = "thinking"
    plan["policy_override"] = override


def apply_expression_style_guard(plan, text):
    if not isinstance(plan, dict):
        return
    if is_comfort_request(text):
        plan["emotion"] = "comforting"
        plan["tts_style"] = "soft"
        plan["face"] = "comforting"
        return
    if is_greeting_request(text):
        plan["emotion"] = "happy"
        plan["tts_style"] = "cheerful"
        plan["face"] = "smile"
        return
    if is_stop_cancel_request(text):
        plan["emotion"] = "neutral"
        plan["tts_style"] = "calm"
        plan["face"] = "neutral"
        return
    if is_surprise_request(text):
        plan["emotion"] = "surprised"
        plan["tts_style"] = "cheerful"
        plan["face"] = "surprised"
        return
    if is_positive_reaction_request(text):
        plan["emotion"] = "happy"
        plan["tts_style"] = "cheerful"
        plan["face"] = "happy"
        return
    if is_uncertain_or_limited_plan(plan):
        plan["emotion"] = "neutral"
        plan["tts_style"] = "calm"
        plan["face"] = "thinking"


def is_uncertain_or_limited_plan(plan):
    reply = str(plan.get("reply", "") or "").lower()
    override = str(plan.get("policy_override", "") or "").lower()
    if any(
        pattern in override
        for pattern in (
            "uncertain",
            "text_unclear",
            "live_external_fact",
            "physical_ability_limit",
            "multi_stage_observation_limit",
        )
    ):
        return True
    return any(
        pattern in reply
        for pattern in (
            "不确定",
            "不能",
            "无法",
            "看不清",
            "よく分かりません",
            "できません",
            "見えません",
            "not sure",
            "cannot",
            "can't",
            "unable",
        )
    )


def apply_user_perspective_guard(plan, text, language):
    if not isinstance(plan, dict) or not is_user_holding_question(text):
        return
    normalized = normalize_reply_language(language)
    reply = str(plan.get("reply", "") or "").strip()
    replacement = ""
    if normalized == "en":
        match = re.match(r"^(?:i\s+am|i['’]m)\s+holding\s+(.+)$", reply, flags=re.IGNORECASE)
        if match:
            obj = match.group(1).strip()
            replacement = f"You appear to be holding {obj}"
        else:
            match = re.match(r"^i\s+hold\s+(.+)$", reply, flags=re.IGNORECASE)
            if match:
                obj = match.group(1).strip()
                replacement = f"You appear to be holding {obj}"
    elif normalized == "zh":
        if reply.startswith("我拿着"):
            replacement = "你拿着" + reply[len("我拿着") :]
        elif reply.startswith("我拿著"):
            replacement = "你拿著" + reply[len("我拿著") :]
        elif reply.startswith("我手里"):
            replacement = "你手里" + reply[len("我手里") :]
        elif reply.startswith("我手裡"):
            replacement = "你手裡" + reply[len("我手裡") :]
    elif normalized == "ja":
        match = re.match(r"^私は(.+?)を持っています[。.]?$", reply)
        if match:
            replacement = f"あなたは{match.group(1).strip()}を持っているようです。"

    if replacement:
        plan["reply"] = replacement
        plan["reply_language"] = normalized
        plan["motion"] = [{"action": "stop", "duration": 0.0}]
        plan["policy_override"] = "visual_reply_quality:user_perspective"


def apply_robot_holding_visual_guard(plan, text, language):
    if not isinstance(plan, dict) or not is_visual_question_request(text):
        return
    normalized = normalize_reply_language(language)
    reply = str(plan.get("reply", "") or "").strip()
    replacement = ""
    if normalized == "en":
        match = re.match(
            r"^(?:the\s+robot|robot)\s+is\s+holding\s+(.+)$",
            reply,
            flags=re.IGNORECASE,
        )
        if match:
            obj = match.group(1).strip()
            replacement = f"It looks like {obj}"
    elif normalized == "zh":
        for prefix in ("机器人拿着", "機器人拿著", "机器人正在拿着", "機器人正在拿著"):
            if reply.startswith(prefix):
                replacement = "看起来像" + reply[len(prefix) :]
                break
    elif normalized == "ja":
        match = re.match(r"^ロボットが(.+?)を持っています[。.]?$", reply)
        if match:
            replacement = f"{match.group(1).strip()}のようです。"
    if replacement:
        plan["reply"] = replacement
        plan["reply_language"] = normalized
        plan["motion"] = [{"action": "stop", "duration": 0.0}]
        plan["policy_override"] = "visual_reply_quality:robot_perspective"


def repair_text_reading_language_mismatch(decision, text, language):
    if decision.accepted or not is_text_reading_request(text):
        return decision
    raw_plan = decision.raw_plan
    if not isinstance(raw_plan, dict):
        return decision
    errors = list(decision.errors or [])
    if not errors or any(not error.startswith("language: reply text does not match") for error in errors):
        return decision
    normalized = normalize_reply_language(language)
    if str(raw_plan.get("reply_language", "") or "").strip().lower() != normalized:
        return decision
    reply = str(raw_plan.get("reply", "") or "").strip()
    if not reply:
        return decision

    repaired = copy.deepcopy(raw_plan)
    repaired["reply"] = reply
    repaired["reply_language"] = normalized
    repaired["validated"] = True
    repaired["fallback_used"] = False
    repaired.setdefault("source", "vlm")
    repaired.setdefault("emotion", "neutral")
    repaired.setdefault("tts_style", "calm")
    repaired.setdefault("face", "thinking")
    repaired["motion"] = [{"action": "stop", "duration": 0.0}]
    repaired["policy_override"] = "visual_reply_quality:ocr_language_mixed"
    return PlanDecision(
        accepted=True,
        fallback_used=False,
        fallback_reason="",
        errors=[],
        plan=repaired,
        raw_plan=copy.deepcopy(raw_plan),
    )


def is_explicit_motion_request(text):
    value = str(text or "").lower()
    no_motion_patterns = (
        "stay still",
        "do not move",
        "don't move",
        "please don't move",
        "do not place",
        "止まって",
        "動かない",
        "動かないで",
        "置かない",
        "不要移动",
        "不要移動",
        "别移动",
        "別移動",
        "请不要移动",
        "請不要移動",
        "待在原地",
        "留在原地",
    )
    if is_stop_cancel_request(value):
        return False
    if any(pattern in value for pattern in no_motion_patterns):
        return False
    patterns = (
        "move",
        "come closer",
        "forward",
        "backward",
        "rotate",
        "turn",
        "look around",
        "scan",
        "動いて",
        "近づ",
        "前に",
        "後ろ",
        "回転",
        "周り",
        "回って",
        "移动",
        "前进",
        "后退",
        "靠近",
        "转",
        "旋转",
        "看看周围",
        "扫描",
    )
    return any(pattern in value for pattern in patterns)


def should_force_stop_only(text):
    value = str(text or "").lower()
    if is_explicit_motion_request(value):
        return False
    patterns = (
        "observe",
        "latest camera frame",
        "latest camel frame",
        "camera frame",
        "camel frame",
        "look at the frame",
        "the frame",
        "respond safely",
        "stay still",
        "do not move",
        "don't move",
        "what is this",
        "what can you see",
        "what do you see",
        "what color is it",
        "what is it",
        "何が見え",
        "見えますか",
        "見えていますか",
        "画像",
        "画面",
        "ご覧",
        "これ",
        "それ",
        "何ですか",
        "何んですか",
        "なんですか",
        "さっき",
        "这是",
        "这是什么",
        "看图",
        "看圖",
        "图",
        "圖",
        "看到什么",
        "看到了什么",
        "能看到",
        "看到的是什么",
        "是什么",
        "刚才",
        "剛才",
        "回答我",
    )
    return any(pattern in value for pattern in patterns)


def make_live_external_fact_plan(trace_id, language):
    normalized = normalize_reply_language(language)
    replies = {
        "zh": "我这里无法确认实时信息。",
        "ja": "ここでは最新情報を確認できません。",
        "en": "I cannot check live information here.",
    }
    return {
        "input_id": trace_id,
        "trace_id": trace_id,
        "source": "policy_guard",
        "validated": True,
        "fallback_used": False,
        "policy_override": "live_external_fact",
        "reply": replies[normalized],
        "reply_language": normalized,
        "emotion": "neutral",
        "tts_style": "calm",
        "face": "thinking",
        "motion": [{"action": "stop", "duration": 0.0}],
    }


def main(args=None):
    rclpy.init(args=args)
    node = VlmBehaviorClient()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
