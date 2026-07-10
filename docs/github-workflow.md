# GitHub Workflow

- Repository: `r1file/tb3-multimodal-interaction`.
- Default branch: `main`.
- Keep deployment changes reviewable through short-lived branches.
- Pull on each host with `git pull --ff-only`; never edit host-specific source.
- Put machine values in ignored `.env` files.
- Tag the first verified three-host migration before removing old package trees.

The runtime hosts use independent read-only deploy keys. Their networks block
GitHub SSH port 22, so each checkout stores a repository-local `core.sshCommand`
that routes SSH through `ssh.github.com:443`. No personal token is copied to a
runtime host.

Before every push:

```bash
git status --short
git diff --check
find . -type f -size +10M -print
rg -n "password|token|secret|BEGIN .*PRIVATE KEY" .
```

Models, caches, recordings, raw logs, and host backups remain outside Git.
