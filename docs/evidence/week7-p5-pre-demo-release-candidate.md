# Week7 P5 pre-demo release candidate

Date: 2026-07-16 (Asia/Tokyo)

Scope: engineering wrap-up only. P4 showcase, physical-scene correctness, and
real-motion acceptance remain open demo gates.

## Repository verification

- `python3 scripts/audit_repository.py`:
  `REPOSITORY_AUDIT_PASS files=145`.
- `bash scripts/validate_repository.sh` from an isolated Python environment:
  shell syntax, Python compilation, both dashboard JavaScript bundles, and all
  automated tests passed.
- Automated tests: `29 passed`.
- A fresh GitHub clone of branch `codex/week7-pre-demo-rc` at commit `25d3ac4`
  independently produced `REPOSITORY_VALIDATION_PASS` with a clean worktree.
- No tracked or unignored credentials, private keys, forbidden model/archive
  artifacts, broken local Markdown links, or files larger than 10 MiB were
  reported.

## Three-host verification

The canonical install and runtime preflights passed on all three roles:

| Role | Install/runtime result | Notes |
| --- | --- | --- |
| AI Max | pass | VLM and mmproj paths made explicit in the host-local `.env`; runtime warnings: 0 |
| Server PC | pass | one retained-legacy-directory warning for rollback compatibility |
| TB3 | pass | one retained-legacy-directory warning for rollback compatibility |

`deploy/role.sh <role> status` reported `overall_state: ready` on AI Max,
Server PC, and TB3. Critical model, dashboard, ROS, relay, bringup, device-stack,
and behavior processes each reported the expected single instance.

The full ROS health check passed with motion safety retained:

```text
TB3_BEHAVIOR_DRY_RUN=true
TB3_STACK_HEALTH_PASS
```

The check covered `/cmd_vel`, `/odom`, motion/expression/face commands, camera,
audio, speech playback, TTS, ASR, and the TB3 face UI endpoint.

## Release boundary

This candidate is ready for code review and clean-checkout reproduction. It is
not a final release: no release tag should be created until the P4 demo matrix,
three clean-start sequences, physical visual/OCR checks, and any explicitly
authorized real-motion row have passed.
