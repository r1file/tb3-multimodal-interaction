# Week 7 P0 Baseline Acceptance - 2026-07-16

## Baseline identity

Before Week 7 changes, the Local Mac, AI Max, Server PC, and TurtleBot3 all had
a clean `main` checkout at commit:

```text
09f67b30dcc9c2abef0860ddb600e9ade10a5b67
```

The verified runtime defaults were Qwen3-VL 8B on `:18082`, ROS domain `30`,
`TB3_BEHAVIOR_DRY_RUN=true`, and maximum behavior duration `1.5 s`.

## Clean-start runtime acceptance

The roles were started in the documented order: AI Max, Server PC, then TB3.

- AI Max: removed obsolete listeners on `:18081` and `:18083`; the only llama
  listener is Qwen3-VL 8B on `:18082`, with the dashboard on `:18181`.
- Server PC: `turtlebot3`, `tb3_asr`, and `tb3_tts` containers are running;
  dashboard `:8775`, VLM client, and status relay are active.
- TB3: bringup, device stack, touch UI `:8765`, and behavior executor are
  active. The persistent executor was restored after hardware smoke testing
  with `dry_run=True`.

Final verification:

- `TB3_STACK_HEALTH_PASS` in `full` mode.
- Server dashboard: `node_count=17`, `stale_nodes=[]`, `missing_nodes=[]`.
- Server services `turtlebot3`, `tb3_asr`, `tb3_tts`, `server_ui`, `vlm`, and
  `behavior`: all `ok`.
- AI Max dashboard relay: `source=relay`, `relay_age_s=0`.

## Fresh three-host trace and correction acceptance

The first attempt exposed that `刚才那个物品是什么？` was classified as a
fresh visual question. Although the correction turn used one context turn and
correctly changed `水杯` to `手机`, the later follow-up cleared context and
returned `不确定`.

Root cause: the context gate recognized several meta-context forms, but not the
temporal-object form `刚才那个...`; visual-question exclusion therefore won.

The fix adds explicit temporal-object patterns while retaining the rule that a
fresh visual question such as `看一下最新画面，这是什么？` uses no old context.
Unit and contract tests on the Server PC passed: `13 passed`.

Live regression result: `WEEK7_CONTEXT_CORRECTION_PASS`.

| Turn | Trace | Result | Context | Total |
|---|---|---|---|---:|
| Baseline | `week7_p0_baseline_1784176549` | `水杯` | `0`, `fresh_request` | 2249 ms |
| Correction | `week7_p0_correction_1784176549` | `手机` | `1`, `correction` | 2222 ms |
| Follow-up | `week7_p0_followup_1784176549` | preserves `手机` | `2`, `meta_context` | 4 ms |

All three turns were accepted without fallback, reached behavior `finished`,
contained only `stop`, and had `effective_dry_run=true`.

## No-motion output smoke

The existing no-motion hardware smoke initially exposed schema drift: its
hand-written plan omitted `reply_language`, so the current validator correctly
rejected it. The smoke was updated to the current schema and now waits for real
TTS and speech completion instead of accepting the first intermediate status.

Final result: `BEHAVIOR_NO_MOTION_HARDWARE_SMOKE_PASS`.

- Plan: accepted, no fallback.
- Motion: `stop` only.
- Face: `thinking` observed.
- TTS: English `af_heart`, `state=done`, latency `4809 ms`, audio `3.225 s`.
- TB3 playback: `speech done`.
- Persistent executor restored with `dry_run=True` after the smoke.

## Format-only JSON retry decision

One automatic VLM retry for format-only failures remains intentionally
deferred. The fresh 8B baseline and correction traces all produced valid plans
without fallback, so current evidence does not justify another model call.
Prompt tightening, deterministic safe repair, validator fallback, and policy
guards remain the current strategy. This decision should be revisited only if
the standardized Week 7 dataset records new format-only failures.

## Evidence and preservation

- Server raw VLM records: `/tmp/vlm_client_logs/vlm_client.jsonl`.
- Server VLM runtime log: `/tmp/vlm_client.log`.
- TB3 no-motion executor log: `/tmp/behavior_no_motion_hardware.log`.
- Current operational dashboards: Server `:8775`, AI Max `:18181`, TB3 `:8765`.
- Historical Week 6 logs were not rewritten.

One Week 7 P3 input was also observed: Server PC and TB3 wall clocks differed by
approximately four seconds during the trace. Cross-host end-to-end latency must
therefore not be calculated by subtracting wall-clock timestamps without clock
synchronization metadata; per-process monotonic durations remain authoritative.
