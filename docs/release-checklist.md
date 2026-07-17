# Week7 platform release checklist

Status: **Week7 engineering complete; formal presentation ready**. A final tag
or GitHub release is a separate publication decision after the presentation.

## Repository and documentation

- [x] Repository audit reports no credential, forbidden artifact, or file over
  10 MiB.
- [x] Shell syntax, Python compilation, dashboard JavaScript, and automated tests
  pass from a clean checkout.
- [x] README and documentation index point only to canonical current entrypoints.
- [x] Reproduction, hardware, limitations, lifecycle, troubleshooting, and
  rollback documentation match the deployed stack.
- [x] Historical Week1-6 names appear only in history/migration/evidence context.

## Reproduction and runtime

- [x] Clean GitHub checkout passes repository validation.
- [x] AI Max, Server PC, and TB3 install/runtime preflights pass.
- [x] All three role statuses are `ready` with one critical instance each.
- [x] Full health passes with `TB3_BEHAVIOR_DRY_RUN=true`.
- [x] Dashboard endpoints and P3 evaluation outputs are readable.

## Demo readiness

- [x] P4 showcase and regression rows are frozen.
- [x] Three clean-start demo sequences pass.
- [x] A post-deployment live I/O smoke covers real ASR, a non-zero camera frame,
  VLM/validation, TTS/playback, face UI, and bounded motion with final stop.
- [x] Final Week7 metrics and the recoverable first-turn ASR timeout are recorded
  without rewriting raw data.
- [x] The formal-presentation run sheet requires scene truth for selected
  visual/OCR rows and explicit floor/emergency-stop authorization for motion.

## Publication

- [x] Pre-demo candidate is committed, pushed, and available for review through
  a draft PR.
- [ ] Runtime hosts are updated to the reviewed commit after merge.
- [ ] Final release notes identify external models/assets and known limitations.
- [ ] Tag and GitHub release are created only when the formal presentation and
  publication review are accepted; this is not a Week7 completion requirement.
