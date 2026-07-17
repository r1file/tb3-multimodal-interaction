# Documentation index

Use current operational documentation for deployment and troubleshooting. Old
Week-numbered material is evidence of how the platform evolved, not an active
runtime instruction.

## Current operator documentation

- [Fresh-host reproduction](reproduction.md): prerequisite through rollback.
- [Official demo runbook](demo-runbook.md): frozen P4 rows, verdicts, and
  operator-only physical gates.
- [P4 demo test table](week7-p4-demo-test-table.md): completed automation versus
  remaining operator-run tests.
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

## Repository maintenance

- [GitHub workflow](github-workflow.md)
- [File lifecycle](file-lifecycle.md)
- [Script classification](script-classification.md)

Run `bash scripts/validate_repository.sh` before publishing. The current
runtime entrypoint is always `bash deploy/role.sh <role> <action>`.

## Historical migration and evidence

- [Pre-migration inventory](inventory.md)
- [Migration map](migration-map.md)
- [P6 migration result](migration-result.md)
- [Week7 evidence](evidence/)

Historical pages deliberately retain old names, paths, metrics, and commands so
past results remain auditable. Do not copy their startup commands into a current
deployment.
