# Week6 P4 Expression / English TTS Completion - 2026-07-09

## Scope

P4 was originally listed as English TTS / Expression stabilization.

Already completed before this pass:

- English TTS language routing in `tts_topic_adapter_node.py`
- English voice default: `af_heart`
- TTS status includes selected `voice`
- Manual expression publish path worked for `happy`

Remaining gap addressed in this pass:

- VLM plans could still choose unstable or neutral `face` / `tts_style` for demo-relevant interaction types.
- Comfort/encouragement prompts were especially unstable in earlier logs, including Japanese ASR variants.

## Code Changes

Updated:

- `tb3_week2_executor/tb3_week2_executor/vlm_behavior_client_node.py`

Changes:

- Added prompt rule for expression/style mapping:
  - greeting -> `smile` / `cheerful`
  - comfort -> `comforting` / `soft`
  - uncertainty or limitation -> `thinking` / `calm`
  - stop/cancel -> `neutral` / `calm`
- Added deterministic comfort policy:
  - `policy_override=comforting_response`
  - zh: `别担心，我在这里。`
  - ja: `大丈夫です。そばにいます。`
  - en: `I am here with you.`
  - face: `comforting`
  - emotion: `comforting`
  - tts_style: `soft`
- Added post-validation `apply_expression_style_guard()` to normalize model-produced plans.
- Added intent recognizers:
  - `is_comfort_request()`
  - `is_positive_reaction_request()`
  - `is_surprise_request()`
  - `is_uncertain_or_limited_plan()`

## Deployment

Deployed to Server PC container:

- `/workspace/ros2_ws/src/tb3_week2_executor/tb3_week2_executor/vlm_behavior_client_node.py`

Rebuilt:

- `colcon build --packages-select tb3_week2_executor --symlink-install`

Restarted through standard host scripts:

- `start_week5_behavior_executor_host.sh`
- `start_week5_vlm_client_host.sh`

Final process snapshot:

- behavior executor parent/child: `337466`, `337471`
- VLM client parent/child: `337547`, `337551`
- TTS adapter child: `307641`

Important runtime note:

- Manual VLM restarts must source:
  - `/workspace/ros2_ws/src/tb3_week2_executor/scripts/week2_ros_env.sh`
- A temporary failed probe happened when VLM was manually restarted without this environment and ran outside `ROS_DOMAIN_ID=30`.
- The standard host scripts already source the correct environment.

## Validation

Local policy checks:

- Greeting English:
  - reply: `Good morning, I am ready.`
  - face: `smile`
  - emotion: `happy`
  - tts_style: `cheerful`
  - accepted: true
- Comfort English:
  - reply: `I am here with you.`
  - face: `comforting`
  - emotion: `comforting`
  - tts_style: `soft`
  - accepted: true
- Comfort Japanese:
  - reply: `大丈夫です。そばにいます。`
  - face: `comforting`
  - emotion: `comforting`
  - tts_style: `soft`
  - accepted: true
- Physical limitation:
  - reply: `I cannot pick up objects here.`
  - face: `thinking`
  - tts_style: `calm`
  - accepted: true

End-to-end run-mode validation:

- request: `I'm a little nervous. Can you comfort me? Please don't move.`
- trace: `p4_comfort_en_run_1783584773439`
- plan:
  - reply: `I am here with you.`
  - reply_language: `en`
  - source: `policy_guard`
  - policy_override: `comforting_response`
  - face: `comforting`
  - emotion: `comforting`
  - tts_style: `soft`
- behavior:
  - state: `finished`
  - effective_dry_run: `false`
- TB3 face UI:
  - expression: `comforting`
- English TTS:
  - state: `done`
  - text: `I am here with you.`
  - language: `en`
  - voice: `af_heart`
  - style: `soft`
  - latency: `826 ms`
  - audio duration: `1.725 s`

Pure English TTS probe:

- trace: `p4_tts_en_probe_1783584862368`
- text: `English voice is ready.`
- state: `done`
- language: `en`
- voice: `af_heart`
- style: `soft`
- latency: `953 ms`
- audio duration: `2.05 s`

## Status

P4 is now complete for demo purposes:

- English TTS works through both direct TTS probe and behavior execution.
- Demo-relevant expression/style mapping is deterministic.
- Comfort/encouragement prompts are no longer dependent on VLM mood selection.
