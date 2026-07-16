# Week7 P3 current-platform baseline

Source: `docs/evidence/model-comparison.json` (preserved; not modified).

| Model | Attempts | Success / warn / fail / missing rows | Fallback | Major error categories | Median ASR / VLM / total ms |
|---|---:|---:|---:|---|---:|
| 2B_full_demo_postfix | 27 | 16/1/3/3 | 1 (3.7%) | missing_trial:3;retry_required:1;scenario_failure:3;visual_evidence_uncertain:5 | 5411 / 1332 / 6747 |
| 8B_full_demo_user_run | 32 | 20/1/2/0 | 6 (18.8%) | model_contract_error:4;retry_required:2;scenario_failure:2;visual_evidence_uncertain:5 | 5411.0 / 3306.5 / 8741.0 |

ASR-related failures and fallback attempts remain in the denominator. Historical records lack trace-linked execution/TTS/playback status, so they are not promoted to full-chain success by the v1 converter.
