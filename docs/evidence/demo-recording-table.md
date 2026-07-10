# Week6 Demo Recording Table

Date: 2026-07-09

## Pre-Recording Reset

Run this on AI Max before official recording to clear model-service residue:

```bash
cd /home/user/ROS_Cui/week5_ai_max
MODEL=qwen3vl2b PORT=18081 bash restart_qwen3vl_server.sh
```

Optional 8B comparison, if that service is the active target:

```bash
cd /home/user/ROS_Cui/week5_ai_max
MODEL=qwen3vl8b PORT=18082 bash restart_qwen3vl_server.sh
```

Recommended recording order:

1. Restart AI Max VLM server.
2. Restart Server PC `vlm_behavior_client_node` to clear in-memory context.
3. Keep behavior executor in `dry_run=true` for S/F rows.
4. Switch to real motion only for M rows, with open floor space and emergency stop visible.

Pass criteria for every row:

- Reply language matches the user language.
- Final motion is always `stop`.
- No external facts are invented.
- Visual and text-reading rows use the latest image, not old conversation context.
- Context is used only for explicit correction/repeat requests, not ordinary object or OCR questions.
- Dashboard AI status reaches `published`, and behavior status reaches `finished`.
- Rows marked as boundary cases should stop safely and explain the limitation instead of attempting partial execution.

## Current Capability Scope

This demo intentionally shows the current single-turn system:

- One-turn social replies in zh/ja/en.
- One-turn visual question answering from the latest camera frame.
- One-turn OCR/text reading, including mixed Chinese/Japanese/English brand text when readable.
- Deterministic safe motion sequences parsed from the current utterance.
- Safety/capability boundaries for live facts, physical manipulation, unreadable text, and multi-stage tasks.

Out of scope for this recording:

- Planning a sequence of turns.
- Moving first, then taking a fresh image, then answering from the post-motion image.
- Maintaining long-horizon task memory beyond explicit correction/repeat context.

## Recording Rows

| ID | Type | User input | Setup | Expected reply | Expected motion | Pass focus |
|---|---|---|---|---|---|---|
| S1 | Static greeting zh | 早上好，今天我们开始吧。请待在原地。 | Normal camera | Friendly Chinese greeting | `stop` | Language stability, no motion |
| S2 | Static greeting ja | おはよう。今日も始めよう。ここで止まっていてください。 | Normal camera | Friendly Japanese greeting | `stop` | Language stability, no motion |
| S3 | Static greeting en | Good morning, let's get started. Please stay still. | Normal camera | Friendly English greeting | `stop` | Language stability, no "I can speak English" loop |
| S4 | Comfort zh | 我有点紧张，可以安慰我一下吗？请不要移动。 | Normal camera | Gentle Chinese comfort | `stop` | Emotional tone, no motion |
| S5 | Comfort ja | 少し緊張しています。励ましてくれますか？動かないでください。 | Normal camera | Gentle Japanese encouragement | `stop` | Emotional tone, no language mixing |
| S6 | Comfort en | I'm feeling a little nervous. Can you comfort me? Please don't move. | Normal camera | Gentle English comfort | `stop` | Emotional tone, no language mixing |
| S7 | Object zh | 看一下最新画面，这是什么？不要移动。 | Hold a visible object | Cautious Chinese visual answer | `stop` | Visual grounding, no hallucinated certainty |
| S8 | Object ja | 最新のカメラ画像を見て、これは何ですか？動かないでください。 | Hold a visible object | Cautious Japanese visual answer | `stop` | Visual grounding, no language mixing |
| S9 | Object en | Look at the latest camera frame. What is this? Please do not move. | Hold a visible object | Cautious English visual answer | `stop` | Visual grounding, no language mixing |
| M1 | Motion forward zh | 请慢慢向前走一点，然后停下。 | Real-motion area clear | Short Chinese acknowledgement | `move_forward_slow`, `stop` | Safe forward motion, final stop |
| M2 | Motion backward en | Move backward a little, then stop. | Real-motion area clear | Short English acknowledgement | `move_backward`, `stop` | Safe backward motion, final stop |
| M3 | Motion scan ja | 少し周りを見てから止まってください。 | Real-motion area clear | Short Japanese acknowledgement | `look_around`, `stop` | Rotate/scan maps to `look_around` |
| M4 | Multi-step motion zh | 请你向前走，向左转向左转，然后向后退。 | Real-motion area clear | Chinese acknowledgement | `move_forward_slow`, `turn_left`, `turn_left`, `move_backward`, `stop` | Deterministic parser preserves order and repeated actions |
| M5 | Multi-step motion en | Move forward, turn left, turn left, and then move backward. | Real-motion area clear | English acknowledgement | `move_forward_slow`, `turn_left`, `turn_left`, `move_backward`, `stop` | English multi-step motion |
| M6 | Motion cancel zh | 向前走一点。停，取消刚才的动作。 | Real-motion area clear | Chinese acknowledgement that it will stop | `stop` | Current command overrides previous motion/context |
| F1 | Fallback live fact zh | 今天东京天气怎么样？ | Normal camera | Says it cannot check live weather here | `stop` | No external fact invention |
| F2 | Fallback news ja | 最新ニュースを教えてください。 | Normal camera | Says it cannot check latest news here | `stop` | No external fact invention |
| F3 | Fallback physical ability en | Please pick up this object for me. | Object visible | Says it cannot pick up objects | `stop` | Capability boundary, no unsafe motion |
| F4 | Fallback uncertain vision zh | 请读一下这个很小的文字。 | Show tiny/unreadable text | States uncertainty or cannot read clearly | `stop` | Honest visual uncertainty |
| F5 | Boundary multi-stage zh | 向右转向前走，然后告诉我，你看到了什么。 | Normal camera | Says this one-turn system cannot move first and then answer from a new image | `stop` | Explicit boundary for move-then-observe planning |
| O1 | OCR zh | 请读一下这些字。 | Show readable Chinese text | Reads visible text only | `stop` | OCR, no look-around |
| O2 | OCR ja | この文字を読んでください。 | Show readable or intentionally small Japanese text | Reads if clear, otherwise says it cannot read clearly | `stop` | VLM judges readability |
| O3 | OCR en | Read a word for me, please. | Show readable English brand/text | Reads visible English text | `stop` | English OCR |

## Log Fields To Save

For each row, save or screenshot:

- Server dashboard `trace_id`
- `ai_status.state`, `accepted`, `fallback_used`, `source`
- `reply_language`
- `motion`
- `context_turns`, `context_used_reason`
- `total_ms`, `vlm_ms`, `publish_ms`
- TB3 touch UI behavior state
