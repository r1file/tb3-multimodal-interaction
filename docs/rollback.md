# P6 Rollback

Do not delete the old package until the renamed package passes a complete
three-host trace.

## Backup roots

- Mac: `/Users/cuibaitao/Documents/Research_backups/p6_20260710_1935JST`
- Server PC: `/home/user/ROS_Cui/backups/p6_20260710_1935JST/server_pc`
- TB3: `/home/turtlebot3/backups/p6_20260710_1935JST/tb3`
- AI Max: `/home/user/ROS_Cui/backups/p6_20260710_1935JST/ai_max`

## Rollback order

1. Stop only the affected role services.
2. Restore the role archive into `/` with `tar -xzf ARCHIVE -C /`.
3. If Server PC model cache was renamed, move `model_cache` back to
   `week3_model_cache` before rebuilding the old ASR image.
4. Rebuild the old ROS package with `colcon build --packages-select
   tb3_week2_executor --symlink-install`.
5. Run the old role startup scripts and old full health check.

Restoring archives is intentionally manual so rollback cannot run accidentally.
