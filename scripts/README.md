# Script policy

Normal operators use only:

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> <install|start|stop|restart|status>
```

The scripts in this directory fall into three support classes:

- `start_*`, `prepare_*`, `stop_matching_processes.py`, and
  `check_tb3_bringup_graph.py`: role-owned implementation helpers.
- `health_check_full.sh`, `smoke_*`, and `wait_*`: repeatable runtime checks.
- `run_demo_matrix.py` and `summarize_demo_matrix.py`: frozen P4 demo execution
  and non-destructive result summarization. Automated runs are always dry-run;
  injected-ASR results are labeled separately and do not satisfy the live-ASR
  gate. Physical-scene truth and real motion remain explicit operator gates.
- `validate_repository.sh`, `audit_repository.py`, baseline builders, and legacy
  standardizers: offline repository/evidence maintenance.

Do not combine component start scripts with a running canonical role. Old
Week-numbered entrypoints are deprecated and intentionally absent from Git;
their mappings remain in `docs/script-classification.md` for rollback history.
