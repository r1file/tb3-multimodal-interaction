# Week6 P3 Context Memory Fix - 2026-07-09

## Problem

The user asked: "刚才我让你看了两件东西，分别是什么？"

Observed log before the fix:

- trace: `tb3_ui_1783582833752`
- text: `刚才我让你看了两件东西，分别是什么？`
- context candidates: `3`
- selected context turns: `0`
- context reason: `fresh_request`
- result: the request was treated as a fresh visual question and answered from the current image.

Root cause:

- `context_relevance_reason()` checked visual/text-reading requests before recognizing meta-context questions.
- The follow-up pattern set was too narrow for "what did I ask / what happened / what were the previous items" style questions.
- Cross-language filtering could remove useful previous turns for meta questions.

## Changes

- Added `is_meta_context_request()` for recent-turn memory questions such as:
  - `刚才我问了什么？`
  - `刚才我让你看了两件东西，分别是什么？`
  - `上一轮/上一步/当前进度/做到哪一步`
  - English/Japanese equivalents.
- `context_relevance_reason()` now returns `meta_context` before visual-question exclusion.
- `allow_cross_language_context()` allows cross-language history for meta-context questions.
- Context prompt now includes motion and policy override metadata and explicitly tells the VLM to summarize recent turns for progress/history questions.
- Added `make_context_policy_plan()`:
  - For meta-context requests with available history, it generates a local `policy_guard` plan.
  - For "分别是什么 / two things" questions, it summarizes useful recent assistant answers in order.
  - This bypasses the VLM call for deterministic memory answers.
- `behavior_plan_contract.py` now allows mixed-language reply text for `policy_override=context_summary`, so quoted previous Japanese/English answers can be included in a Chinese summary without validator fallback.

## Deployment

Deployed to Server PC container `turtlebot3`:

- `/workspace/ros2_ws/src/tb3_week2_executor/tb3_week2_executor/vlm_behavior_client_node.py`
- `/workspace/ros2_ws/src/tb3_week2_executor/tb3_week2_executor/behavior_plan_contract.py`

Rebuilt:

- `colcon build --packages-select tb3_week2_executor --symlink-install`

Restarted:

- `behavior_executor_node`, `dry_run:=false`
- `vlm_behavior_client_node`, `llama_base_url:=http://192.168.64.246:18081`, `model:=qwen3vl2b`, `publish_plans:=true`

Running PIDs after restart:

- behavior executor parent/child: `332548`, `332555`
- VLM client parent/child: `332549`, `332556`

## Smoke Test

Session: `p3_context_smoke:memory`

1. `请只回答手机两个字。`
   - reply: `手机`
   - context: `0`, reason: `fresh_request`

2. `请只回答鼠标两个字。`
   - reply: `鼠标`
   - context: `0`, reason: `fresh_request`

3. `刚才我让你回答了两件东西，分别是什么？`
   - context: `2`
   - reason: `meta_context`
   - reply: `刚才我分别回答：手机；鼠标。`
   - source: `policy_guard`
   - policy override: `context_summary`
   - fallback: `false`
   - VLM latency: `0 ms`

4. `这是什么？`
   - context: `0`
   - reason: `fresh_request`
   - confirms fresh visual questions are still not polluted by memory.

Latest pulled verification log:

- `week6_logs/full_demo_20260709_after_prompt/week5_vlm_client_p3_after_fix.jsonl`
