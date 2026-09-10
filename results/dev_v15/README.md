# Interview snapshot: dev_v15

This saved run contains **10 completed episodes, zero failed attempts**: `gpt-5.6-luna` and `gpt-5.6-terra` each evaluated once on five matched scenarios, one per difficulty level. Model identifiers are those recorded in the run; no new model calls were made to prepare this folder for sharing.

Start with the [comparison viewer](luna_vs_terra.html) (download and open locally), the [leaderboard](leaderboard.md), and the [failure analysis](../../README_INTERVIEW.md#failure-analysis-where-models-lose-credit).

| Difficulty / scenario | Luna trajectory | Terra trajectory |
|---|---|---|
| 1 / l1_01000 | [JSON gzip](traces/l1_01000__gpt-5.6-luna.json.gz) | [JSON gzip](traces/l1_01000__gpt-5.6-terra.json.gz) |
| 2 / l2_01010 | [JSON gzip](traces/l2_01010__gpt-5.6-luna.json.gz) | [JSON gzip](traces/l2_01010__gpt-5.6-terra.json.gz) |
| 3 / l3_01020 | [JSON gzip](traces/l3_01020__gpt-5.6-luna.json.gz) | [JSON gzip](traces/l3_01020__gpt-5.6-terra.json.gz) |
| 4 / l4_01030 | [JSON gzip](traces/l4_01030__gpt-5.6-luna.json.gz) | [JSON gzip](traces/l4_01030__gpt-5.6-terra.json.gz) |
| 5 / l5_01040 | [JSON gzip](traces/l5_01040__gpt-5.6-luna.json.gz) | [JSON gzip](traces/l5_01040__gpt-5.6-terra.json.gz) |

To render an individual trajectory from the repository root, after installing dependencies:

```sh
uv run execbench view results/dev_v15/traces/l5_01040__gpt-5.6-terra.json.gz \
  --out traces/terra-l5.html
```

Open the resulting HTML locally. Reading and rendering saved traces requires no API key and does not rerun the policy or grader.

## Provenance and interpretation

- [Full scenario set](../../scenarios/v1): 50 generated scenarios, ten per difficulty level. [Development subset](../../scenarios/v1_dev): five byte-identical selections, seeds 1000, 1010, 1020, 1030, and 1040.
- [Manifest](manifest.json): original implementation SHA-256, exact scenario hashes, 60,000-character history setting, provider configuration, and `GLM-5.3-Flash` grader. On September 9, 2026, the implementation hash matched the checked-in package, all five scenario hashes matched `v1_dev`, and each trace embedded the corresponding scenario exactly.
- [Run status](run_status.json), [episode scores](scores.jsonl), and [JSON leaderboard](leaderboard.json) preserve the original run's accounting. The six examples in [demo/dev-v15](../../demo/dev-v15/README.md) are unchanged copies from this run, not extra episodes.
- Outcome means are 0.872 for Terra and 0.710 for Luna; mean simulated compute use is 72.9% and 59.9%, respectively. These are descriptive single-run results, not a pass rate, causal estimate, or statistical model ranking. Dollar costs are unavailable because pricing was not configured.
- Report honesty and coaching use saved model judgments. Deterministic outcome accounting and hidden states should be inspected separately from those judgments. Full traces expose evaluator ground truth for review; ordinary policy observations do not contain it.
- `dev_v15` is a run label and `v1` a scenario-set label; the package and trace schema remain version `0.1.0`. Earlier `demo/live*` results belong to different runs and configurations.

Keep this folder as a frozen review snapshot. Run new experiments into a different output directory. Raw response-cache files and credentials are not part of this submission; the trajectories preserve executed actions and recorded evidence, but a fresh live run is not guaranteed to reproduce the same responses.
