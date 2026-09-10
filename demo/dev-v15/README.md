# dev_v15 failure-analysis evidence

This directory preserves six selected trajectories and summary metadata from the local `results/dev_v15` run to support the [interviewer README](../../README_INTERVIEW.md#failure-analysis-where-models-lose-credit). Files were copied unchanged on September 9, 2026; no models or graders were rerun.

The [complete ten-trajectory run](../../results/dev_v15/README.md) and [source scenarios](../../scenarios/README.md) are now included in the repository. This directory retains the original six-example bundle; its files do not represent additional episodes.

The full run has ten completed episodes and zero failed attempts: five scenarios, one episode per policy per scenario. The [leaderboard](leaderboard.md) and [score records](scores.jsonl) cover all ten; only the six traces cited in the analysis are included here. The [manifest](manifest.json) records the original implementation hash, scenario hashes, and `GLM-5.3-Flash` grader. [Run status](run_status.json) records completion. Dollar costs are unknown, not zero.

| Scenario | Luna | Terra |
|---|---|---|
| L2 rate limiting | [Trace](l2_01010__gpt-5.6-luna.json.gz) | [Trace](l2_01010__gpt-5.6-terra.json.gz) |
| L4 logging migration | [Trace](l4_01030__gpt-5.6-luna.json.gz) | [Trace](l4_01030__gpt-5.6-terra.json.gz) |
| L5 data export | [Trace](l5_01040__gpt-5.6-luna.json.gz) | [Trace](l5_01040__gpt-5.6-terra.json.gz) |

From the repository root, render a saved trace without API calls:

```sh
uv run execbench view demo/dev-v15/l5_01040__gpt-5.6-terra.json.gz \
  --out traces/dev-v15-terra-l5.html
```

Open the output HTML locally. For direct inspection, decompress a trace as JSON: `steps` contains original indices, actions, observations, errors, and hidden states; `scores` contains the final benchmark scores; `explanations` records their accounting; `grading` includes the saved narrative judge output. The judge's own `honesty_score` field is informational: the authoritative result is `scores.report_honesty`, recomputed by Python from claim counts and omissions.

These are development examples, not a held-out evaluation or a statistically reliable model ranking. Full hidden states are included for reviewers and were not ordinary policy observations. Read the saved evidence without regrading it under a changed implementation.
