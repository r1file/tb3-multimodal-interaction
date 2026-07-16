# Week7 P4 automated rehearsal

Date: 2026-07-16 (Asia/Tokyo)

Scope: all P4 work that does not require a person to provide live speech,
arrange and confirm a physical visual/OCR scene, or authorize real motion. Raw
JSONL remains in the Server PC external runtime-log directory and was not added
to Git.

## Frozen demo contract

- Added `tb3_official_demo_matrix@1.0.0` with 14 rows: 8 showcase, 5
  regression, and 1 stress row.
- Coverage includes zh/ja/en social interaction, current-frame visual QA,
  Japanese/English OCR, bounded motion, cancel/stop, live facts/news,
  manipulation, autonomous navigation/mapping, move-then-observe, and unreadable
  text.
- Every row records allowed input paths, setup, expected reply language,
  preferred face set, exact motion sequence, fallback/boundary behavior, manual
  truth checks, warnings, and failures.
- The canonical operator procedure is `docs/demo-runbook.md`; the older Week6
  recording table remains historical evidence only.

## Automated and technical runs

| Run | Rows | Result | Meaning |
| --- | ---: | --- | --- |
| text-only | 9 | 8 pass, 1 warn, 0 fail | social, dry-run motion/cancel, and four non-capability boundaries |
| injected ASR | 9 | 8 pass, 1 warn, 0 fail | cached-ASR consumption only; not counted as live microphone ASR |
| text + camera transport | 5 | 4 warn, 1 initial fail | all rows used non-zero image bytes; visual/OCR truth intentionally remained manual |
| boundary retries | 2 | move-then-observe warn, navigation pass | deterministic guards loaded after the initial failure fix |

The motion warning is expected: `move_forward_slow, stop` passed in dry-run, but
the real-motion gate remains open. Camera rows remain warnings until the operator
compares each answer with the exact physical scene and AI Max Input Inspector
image.

## Failure found and fixed

Initial trace `p4_p4_b_moveobs_ja_1784201017774` safely produced only `stop`,
but its reply incorrectly claimed that the robot would move. The Japanese phrase
“動いてから新しい画像を見て” did not match the existing move-then-observe
guard and fell through to the generic deterministic-motion policy.

The policy now recognizes Japanese motion-then-observation phrasing before
motion parsing. Autonomous navigation/mapping requests also receive a
deterministic capability-boundary response instead of relying on model choice.

- Retry `p4_p4_b_moveobs_ja_1784201184065`: policy
  `multi_stage_observation_limit`, reply explicitly states the limitation,
  motion `stop`, image bytes `44328`; technical verdict warn pending scene truth.
- Retry `p4_p4_b_nav_zh_1784201195523`: policy
  `autonomous_navigation_limit`, reply states navigation/mapping is unavailable,
  motion `stop`; verdict pass.

## Context and process dependency audit

- 18 text and injected-ASR results used 18 unique context sessions.
- Maximum `context_turns` was 0; no ordinary row consumed stale context.
- Every automated result reported dry-run; no physical output was requested.
- AI Max, Server PC, and TB3 all reported `overall_state=ready` with the expected
  single critical instances.
- No active process command matched `tb3_week2_executor`, `start_week1` through
  `start_week6`, or `week5_`.
- All starts used `deploy/role.sh`; no manually launched hidden component was
  needed.

## Three clean-start sequences

Each counted sequence fully stopped TB3, Server PC, and AI Max in reverse order,
then started AI Max, Server PC, and TB3 in deployment order. Role status and full
health were required after every sequence.

| Sequence | AI Max ready | Server PC ready | TB3 ready | Full health |
| --- | ---: | ---: | ---: | --- |
| 1 | 5 s | 8 s | 78 s | `TB3_STACK_HEALTH_PASS` |
| 2 | 5 s | 8 s | 79 s | `TB3_STACK_HEALTH_PASS` |
| 3 | 5 s | 8 s | 81 s | `TB3_STACK_HEALTH_PASS` |

All three sequences retained `TB3_BEHAVIOR_DRY_RUN=true`. An earlier uncounted
rehearsal completed platform startup but its local evidence wrapper had an
invalid `grep` escape; it was excluded rather than presented as a passed
sequence.

## Test results

- Repository-safe local validation: 36 passed.
- Complete Server ROS-container suite after policy changes: 38 passed.
- Repository audit: 152 files passed.

## Remaining operator gates

- live microphone ASR for applicable rows;
- live ASR + current camera for applicable rows;
- physical-scene correctness for visual QA and OCR, including deliberate
  unreadable text;
- one explicitly authorized real-motion `P4-MOTION-ZH` run after the documented
  floor and emergency-stop checklist;
- final official-demo acceptance and release tagging.
