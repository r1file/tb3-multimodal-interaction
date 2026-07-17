# Documentation index

Use current operational documentation for deployment and troubleshooting. Old
Week-numbered material is evidence of how the platform evolved, not an active
runtime instruction.

## Current operator documentation

- [Fresh-host reproduction](reproduction.md): prerequisite through rollback.
- [Official demo runbook](demo-runbook.md): canonical execution, verdict, and
  physical-safety procedure.
- [Formal demo run sheet](week7-p4-demo-test-table.md): presentation order,
  exact prompts, live cues, abort rules, and the extended scenario library.
- [Prerequisites and external assets](prerequisites.md): tested hosts, versions,
  models, credentials, paths, and network assumptions.
- [Preflight](preflight.md): read-only install and runtime readiness checks.
- [Deployment](deployment.md): concise canonical role commands.
- [Lifecycle and logs](lifecycle.md): ownership, idempotence, state vocabulary,
  retention, and log locations.
- [Hardware contract](hardware.md): camera, audio, display, OpenCR, LiDAR, and
  `cmd_vel` discovery.
- [Troubleshooting](troubleshooting.md) and [rollback](rollback.md).
- [Known limitations](limitations.md) and
  [release checklist](release-checklist.md).
- [Architecture](architecture.md) and
  [evaluation schema](evaluation-schema.md).

## Weekly report

- [7/20 report](7-20-report.md): Week7 productization, demo hardening, UI
  redesign, technical evidence, research boundary, and Week8 handoff.

## Repository maintenance

- [GitHub workflow](github-workflow.md)
- [File lifecycle](file-lifecycle.md)
- [Script classification](script-classification.md)

Run `bash scripts/validate_repository.sh` before publishing. The current
runtime entrypoint is always `bash deploy/role.sh <role> <action>`.

## Historical migration and research evidence

- [Pre-migration inventory](inventory.md)
- [Migration map](migration-map.md)
- [P6 migration result](migration-result.md)
- [Model comparison and research validation](evidence/)

Historical migration pages retain old names, paths, metrics, and commands so
past results remain auditable. Phase-by-phase engineering logs are kept in the
project workspace rather than shipped as product documentation. Do not copy old
startup commands into a current deployment.
