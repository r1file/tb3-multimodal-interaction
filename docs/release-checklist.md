# Week7 pre-demo release checklist

Status: **pre-demo release candidate**. Engineering wrap-up may be reviewed and
merged before P4, but no final release tag is created until demo and physical
safety gates are complete.

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

## Open demo gates

- [ ] P4 showcase and regression rows are frozen.
- [ ] Three clean-start demo sequences pass.
- [ ] Visual/OCR answers are checked against the physical scene.
- [ ] Any real-motion row passes the user-controlled floor and emergency-stop
  check after dry-run.
- [ ] Final metrics and known failures are recorded without rewriting raw data.

## Publication

- [x] Pre-demo candidate is committed, pushed, and available for review through
  a draft PR.
- [ ] Runtime hosts are updated to the reviewed commit after merge.
- [ ] Final release notes identify external models/assets and known limitations.
- [ ] Tag and GitHub release are created only after all open demo gates pass.
