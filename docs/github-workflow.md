# GitHub Workflow

- Repository: `r1file/tb3-multimodal-interaction`.
- Default branch: `main`.
- Keep deployment changes reviewable through short-lived branches.
- Run `bash scripts/validate_repository.sh` before staging.
- Pull on each host with `git pull --ff-only`; never edit host-specific source.
- Put the complete topology in one ignored/external host manifest; never edit
  source on one runtime host.
- Tag the first verified three-host migration before removing old package trees.

The runtime hosts use independent read-only deploy keys. Their networks block
GitHub SSH port 22, so each checkout stores a repository-local `core.sshCommand`
that routes SSH through `ssh.github.com:443`. No personal token is copied to a
runtime host.

The exact read-only key creation, repository setting, port-443 SSH command and
verification procedure is in
[Fresh-host prerequisites](prerequisites.md#read-only-github-deploy-key-over-port-443).

Before every push:

```bash
git status --short
git diff --check
find . -type f -size +10M -print
python3 scripts/audit_repository.py
bash scripts/validate_repository.sh
```

Models, caches, recordings, raw logs, and host backups remain outside Git.

Changes from the default branch are published through a short-lived branch and
draft pull request. Runtime hosts keep read-only deploy keys and consume a
reviewed commit only after it is merged. A pre-demo release candidate may be
pushed and reviewed before physical-demo acceptance, but it must not receive a
final release tag until the open demo gates in
[release-checklist.md](release-checklist.md) are complete.
