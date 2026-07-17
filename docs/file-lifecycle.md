# File Lifecycle

## Keep in Git

- ROS 2 package source, launch files, configs, and tests.
- Functional startup, health, and smoke scripts.
- Dockerfiles and role-specific Compose templates.
- AI Max llama.cpp wrappers and read-only dashboard.
- Host-manifest template, deployment, migration, rollback, and architecture docs.
- Small JSON/TXT fixtures and summarized evaluation Markdown/JSON.

## Archive outside Git

- Raw Week2-Week6 JSONL/CSV logs and recordings.
- One-off investigation scripts that are not reproducible tools.
- Old package trees after the new full chain passes.
- Timestamped runtime backups and host-state snapshots.

## Delete candidates after acceptance

- `__pycache__`, `.pyc`, `.DS_Store`, stale PID files, and temporary logs.
- Duplicate copies of identical source files on individual hosts.
- Old stage-numbered startup and smoke scripts after rollback expiry.
- Superseded Dockerfile and Compose backups after remote archive retention is
  confirmed.

## Never commit

- GGUF models, Hugging Face caches, SenseVoice model cache, WAV/MP4 data.
- Passwords, SSH material, tokens, populated host manifests, or machine keyrings.
- Large generated build/install/log directories.
