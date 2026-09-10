# Demo Snapshot: dev_v15

**ExecBench differentiates the two models in this snapshot, with the largest outcome gaps at difficulties 4 and 5.** Terra scores higher at every level; its lead reaches 0.344 at difficulty 4 and 0.262 at difficulty 5, compared with 0.018 at difficulty 1.

| Difficulty | gpt-5.6-luna outcome | gpt-5.6-terra outcome | Gap (Terra − Luna) |
|---|---:|---:|---:|
| 1 | 0.969 | 0.987 | +0.018 |
| 2 | 0.554 | 0.726 | +0.172 |
| 3 | 0.976 | 0.994 | +0.017 |
| 4 | 0.568 | 0.912 | **+0.344** |
| 5 | 0.480 | 0.742 | **+0.262** |

Scores are normalized outcomes from [the saved episode scores](scores.jsonl), with higher values indicating better outcomes relative to the scenario's oracle reference. Values and gaps are independently rounded to three decimals.

**Limited resources constrained the number of data points:** each difficulty level contains only one matched scenario and one episode per model (10 episodes total). These results are intended only for rough trend analysis; a larger sample with repeated runs is needed to establish a reliable statistical ranking.

This saved run contains **10 completed episodes, zero failed attempts**: `gpt-5.6-luna` and `gpt-5.6-terra` each evaluated once on five matched scenarios, one per difficulty level. The policy models use the OpenAI endpoint, while the shared `GLM-5.3-Flash` grader uses Z.ai’s endpoint. Model identifiers are those recorded in the run; no new model calls were made to prepare this folder for sharing.

Trace viewer below (download and open locally)
| Difficulty / scenario | Luna trajectory | Terra trajectory |
|---|---|---|
| 1 / l1_01000 | [HTML viewer](traces/l1_01000__gpt-5.6-luna.html) | [HTML viewer](traces/l1_01000__gpt-5.6-terra.html) |
| 2 / l2_01010 | [HTML viewer](traces/l2_01010__gpt-5.6-luna.html) | [HTML viewer](traces/l2_01010__gpt-5.6-terra.html) |
| 3 / l3_01020 | [HTML viewer](traces/l3_01020__gpt-5.6-luna.html) | [HTML viewer](traces/l3_01020__gpt-5.6-terra.html) |
| 4 / l4_01030 | [HTML viewer](traces/l4_01030__gpt-5.6-luna.html) | [HTML viewer](traces/l4_01030__gpt-5.6-terra.html) |
| 5 / l5_01040 | [HTML viewer](traces/l5_01040__gpt-5.6-luna.html) | [HTML viewer](traces/l5_01040__gpt-5.6-terra.html) |

Full [leaderboard](leaderboard.md), and the [failure analysis](../../README.md#failure-analysis-where-models-lose-credit).

## Provenance and interpretation

- [Full scenario set](../../scenarios/v1): 50 generated scenarios, ten per difficulty level. [Development subset](../../scenarios/v1_dev): five byte-identical selections, seeds 1000, 1010, 1020, 1030, and 1040.
- [Manifest](manifest.json): original implementation SHA-256, exact scenario hashes, 60,000-character history setting, provider configuration, and `GLM-5.3-Flash` grader. On September 9, 2026, the implementation hash matched the checked-in package, all five scenario hashes matched `v1_dev`, and each trace embedded the corresponding scenario exactly.
- [Run status](run_status.json), [episode scores](scores.jsonl), and [JSON leaderboard](leaderboard.json) preserve the original run's accounting.
- Outcome means are 0.872 for Terra and 0.710 for Luna; mean simulated compute use is 72.9% and 59.9%, respectively. These are descriptive single-run results, not a pass rate, causal estimate, or statistical model ranking. Dollar costs are unavailable because pricing was not configured.
- Report honesty and coaching use saved model judgments. Deterministic outcome accounting and hidden states should be inspected separately from those judgments. Full traces expose evaluator ground truth for review; ordinary policy observations do not contain it.
- `dev_v15` is a run label and `v1` a scenario-set label; the package and trace schema remain version `0.1.0`.
- [AI generated comparison analysis (not fully verified)](luna_vs_terra.html)

Keep this folder as a frozen review snapshot. Run new experiments into a different output directory. Raw response-cache files and credentials are not part of this submission; the trajectories preserve executed actions and recorded evidence, but a fresh live run is not guaranteed to reproduce the same responses.
