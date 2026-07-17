# Week7 closeout evidence

Date: 2026-07-17 (Asia/Tokyo)

## Decision

Week7 is complete. The week delivered a reproducible, diagnosable platform
baseline. Repeating the entire Week6-style physical showcase is not a Week7 exit
gate because the Week7 changes were lifecycle, observability, evaluation,
frontend, safety-boundary, and delivery work. The engineering baseline plus a
targeted post-deployment physical I/O smoke is the proportional acceptance.

The frozen 14-row matrix remains the formal-presentation scenario library and a
future regression asset. It is not evidence that every physical scene was run
on 2026-07-17.

## Runtime status after canonical deployment

- AI Max: `overall_state=ready`; llama health and dashboard ready; one
  llama-server process.
- Server PC: `overall_state=ready`; Server dashboard ready; one server control,
  VLM client, evaluation logger, and status relay.
- TB3: `overall_state=ready`; bringup, device stack, face UI, and behavior
  executor ready; critical processes single-instance.

## Targeted physical I/O smoke

Four live UI traces were written after deployment:

1. `tb3_ui_1784275863858`: `degraded` because ASR timed out. The policy guard
   produced a stop-only plan and the retry prompt was synthesized and played.
   No unsafe continuation occurred.
2. `tb3_ui_1784275891992`: `success`; live ASR, 41,036-byte camera frame, VLM,
   validation, TTS, playback, and stop-only execution succeeded.
3. `tb3_ui_1784275909463`: `success`; live ASR/camera and the bounded
   forward/backward sequence completed with final stop.
4. `tb3_ui_1784275927158`: `success`; live ASR, 39,093-byte camera frame, VLM,
   validation, TTS (`1,496 ms`), playback (`2,858 ms`), and bounded
   `move_forward_slow:0.8s > turn_left:0.8s > move_backward:0.8s > stop`
   execution all succeeded.

The TB3 device log independently recorded `Executing turn_left for 0.80s` and
the terminal stop events. Face state was reachable and returned to `neutral`.

Raw runtime records remain outside Git at:

`/home/user/ROS_Cui/turtlebot3/docker/jazzy/workspace/runtime_logs/tb3_multimodal_interaction/evaluation/single_turn_v1.jsonl`

## Week7 completion

- P0 baseline acceptance: complete.
- P1 prerequisites and fresh-host reproduction: complete.
- P2 lifecycle and diagnostics: complete.
- P3 evaluation schema and baseline: complete.
- P3.5 full-chain observability: complete.
- P4 demo hardening and proportional physical I/O acceptance: complete.
- P5 documentation and Week8 handoff: complete.

Known limitations remain documented and are not silently converted into
successes. In particular, live ASR can have a recoverable first-turn timeout,
and visual/OCR semantics still require scene truth when those rows are selected
for a formal presentation.
