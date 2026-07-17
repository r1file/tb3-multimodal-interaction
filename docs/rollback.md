# Release rollback

Rollback changes the deployment from one reviewed `commit + manifest` pair to
an earlier reviewed pair. It never extracts an archive over a running role.

1. Save status JSON, preflight output and the current manifest SHA-256.
2. Stop the affected roles in reverse order with the current manifest.
3. Verify the earlier manifest and commit are available and that external asset
   hashes still match.
4. Check out the earlier commit as a clean detached checkout at that role's
   `repo_dir`; keep the replaced checkout outside `ros_workspace_dir/ros2_ws/src`.
5. Run install preflight, `role.sh <role> install`, start in normal order, status
   and runtime preflight with the earlier manifest.
6. Retain both manifests, checkout backups and logs until post-rollback health
   is accepted.

Timestamped `manifest_runtime_backup_*` directories preserve Compose/UI files
replaced by install. They are diagnostic inputs, not an automatic restore
mechanism. Historical P6 archives remain historical evidence and are not the
current release rollback contract.
