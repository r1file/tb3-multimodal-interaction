# Official demo runbook

This is the canonical formal-presentation operator procedure. The frozen machine-readable source
is [`config/week7_p4_demo_matrix.json`](../config/week7_p4_demo_matrix.json).
Historical Week6 recording tables are evidence only and must not be used for
startup commands or final acceptance.

## Scope and row classes

The matrix contains 14 rows:

- **Showcase (8):** Chinese/Japanese/English social interaction, current-frame
  visual QA, Japanese/English OCR, bounded forward motion, and cancel/stop.
- **Regression (5):** live facts/news, manipulation, autonomous navigation, and
  move-then-observe capability boundaries.
- **Stress (1):** deliberately unreadable text and honest visual uncertainty.

Every row freezes the user input, allowed paths, setup, expected language,
preferred face set, exact planned action sequence, fallback/boundary behavior,
and pass/warn/fail review rules.

## 1. Reset and start in canonical order

Use only the role lifecycle interface. Start AI Max, then Server PC, then TB3:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> stop
bash deploy/role.sh <ai_max|server_pc|tb3> start
bash deploy/role.sh <ai_max|server_pc|tb3> status
bash deploy/preflight.sh <ai_max|server_pc|tb3> --phase runtime
```

Stop roles in reverse order. Do not manually launch llama-server, the Server
status relay, ROS nodes, Xorg/Openbox, or Epiphany alongside the role scripts.

Before every sequence record:

- Git commit on all three hosts;
- startup-to-ready time and any warnings/failures;
- three role status JSON documents;
- `TB3_STACK_HEALTH_PASS` with `TB3_BEHAVIOR_DRY_RUN=true`;
- critical-process counts from role status.

## 2. Validate and inspect the frozen matrix

Inside the Server ROS container:

```bash
python3 /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/run_demo_matrix.py \
  --matrix /workspace/ros2_ws/src/tb3_multimodal_interaction/config/week7_p4_demo_matrix.json \
  --output /tmp/not-written.jsonl \
  --input-path text \
  --validate-only
```

Expected: `DEMO_MATRIX_VALID scenarios=14`.

## 3. Automated no-motion baseline

Raw results belong in the external runtime-log directory, never in Git:

```bash
python3 /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/run_demo_matrix.py \
  --matrix /workspace/ros2_ws/src/tb3_multimodal_interaction/config/week7_p4_demo_matrix.json \
  --output /workspace/runtime_logs/tb3_multimodal_interaction/evaluation/p4_text.jsonl \
  --input-path text
```

This runs every eligible text-only row through the current VLM and behavior
stack. All behavior remains `effective_dry_run=true`; motion rows validate the
planned sequence without moving the robot.

An injected-ASR regression can exercise cached-ASR consumption without asking a
person to speak:

```bash
python3 /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/run_demo_matrix.py \
  --matrix /workspace/ros2_ws/src/tb3_multimodal_interaction/config/week7_p4_demo_matrix.json \
  --output /workspace/runtime_logs/tb3_multimodal_interaction/evaluation/p4_asr_injected.jsonl \
  --input-path asr_injected
```

Injected ASR is labeled `asr_injected`; it is regression evidence, not a live
microphone check.

Summarize without modifying the raw files:

```bash
python3 /workspace/ros2_ws/src/tb3_multimodal_interaction/scripts/summarize_demo_matrix.py \
  --matrix /workspace/ros2_ws/src/tb3_multimodal_interaction/config/week7_p4_demo_matrix.json \
  --results /workspace/runtime_logs/tb3_multimodal_interaction/evaluation/p4_text.jsonl \
  --markdown /tmp/p4-summary.md
```

## 4. Operator-run live paths

Use the Server PC UI at `http://127.0.0.1:8775` and execute the matrix text
exactly. Do not paraphrase during the frozen acceptance run.

- `asr`: press the AI Response control, speak the row, and verify the resolved
  ASR text before judging the response.
- `text_camera`: arrange the row's physical scene, confirm the current preview,
  then submit the exact text.
- `asr_camera`: arrange the scene, press AI Response, speak the exact text, and
  verify both the resolved transcript and submitted image in the dashboards.

For every visual/OCR row, record the physical ground truth before the request.
`image_bytes > 0` proves transport only; it does not prove the answer is correct.
Judge the answer against the exact image shown in the AI Max Input Inspector.

## 5. Real-motion authorization gate

The automated runner never enables real motion. `P4-MOTION-ZH` may be repeated
with real motion only after all of these are true:

- dry-run row passed with `move_forward_slow, stop` in that order;
- open floor and wheel clearance were inspected;
- the robot is on the floor, not a desk or stand;
- battery, OpenCR, lidar, and odometry are healthy;
- emergency stop / motor-power control is visible and reachable;
- one operator is dedicated to the robot;
- `TB3_BEHAVIOR_MAX_DURATION` remains at the documented bound;
- the user explicitly authorizes this particular run.

Abort on unexpected direction, duration, obstacle approach, ROS loss, or missing
final stop. Restore `TB3_BEHAVIOR_DRY_RUN=true` immediately after the row.

## 6. Verdict recording

Use three verdicts consistently:

- **pass:** every automated check and required manual truth check passes;
- **warn:** safe and usable, but only a row-defined warning condition occurs;
- **fail:** any row/global fail rule occurs, a required terminal state is
  missing, or physical truth cannot be established.

Do not convert an unreviewed physical-scene row to pass. Keep failed raw data and
append a new `trial_id` after a fix; never rewrite the earlier trial.

## 7. Completion boundary

Week7 engineering acceptance required the frozen matrix, automated regressions,
three clean-start sequences, safety boundaries, operator documentation, and one
targeted post-deployment physical I/O smoke. That boundary was met on
2026-07-17 and is summarized in [`7-20-report.md`](7-20-report.md).

A formal presentation selects the rows appropriate to its audience and records
physical truth for each selected visual/OCR row. Those presentation-day checks
and any later release/tag decision do not reopen Week7. They must still follow
the safety and evidence rules in this runbook.
