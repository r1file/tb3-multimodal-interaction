# Week6 P5 2B vs 8B Demo Statistics

Date: 2026-07-09

Note: updated after F5補測. Prompt-tightening dry-run regressions are stored separately and are not counted as full-chain demo rows.

## Overall

| Model run | Attempts | Rows attempted | Missing rows | Row best pass/warn/fail/missing | Fallback attempts | Fallback rate | Median total ms | Median VLM ms | Behavior finished |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2B_full_demo_postfix | 27 | 20 | 3 | 16/1/3/3 | 1 | 3.70% | 6747 | 1332 | True |
| 8B_full_demo_user_run | 32 | 23 | 0 | 20/1/2/0 | 6 | 18.75% | 8741.0 | 3306.5 | True |

## 8B Remaining Rows

- `S9` Object en: 8B `pass`, attempts/fallbacks `3/1`, trace `tb3_ui_1783587291882`, notes `passed after retry; had warning attempts; raw output missing contract fields; requires live-frame review`
- `F4` Fallback uncertain vision zh: 8B `warn`, attempts/fallbacks `1/0`, trace `tb3_ui_1783587556048`, notes `requires live-frame review`
- `O1` OCR zh: 8B `fail`, attempts/fallbacks `2/2`, trace `tb3_ui_1783587695687`, notes `raw output missing contract fields`
- `O2` OCR ja: 8B `pass`, attempts/fallbacks `4/2`, trace `tb3_ui_1783587724976`, notes `passed after retry; raw output missing contract fields; requires live-frame review`
- `O3` OCR en: 8B `fail`, attempts/fallbacks `2/1`, trace `tb3_ui_1783587629154`, notes `raw output missing contract fields`

## Output Files

- `week6_2b_vs_8b_demo_stats_20260709.json`
- `week6_2b_vs_8b_attempts_20260709.csv`
- `week6_2b_vs_8b_row_summaries_20260709.csv`
- `week6_2b_vs_8b_row_comparison_20260709.csv`