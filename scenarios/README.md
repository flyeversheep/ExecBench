# Scenario sets

| Directory | Contents | Intended use |
|---|---|---|
| [v1](v1) | 50 fixed-seed scenarios, seeds 1000–1049; ten at each of five difficulty levels | Full generated interview dataset |
| [v1_dev](v1_dev) | Seeds 1000, 1010, 1020, 1030, 1040; byte-identical copies from v1 | Five-scenario development sweep used by [dev_v15](../results/dev_v15/README.md) |
| [v0](v0) | Earlier 50-scenario generation | Provenance for historical baseline/live demos |

Each JSON file includes the public project setup, hidden simulator state, configuration, generation provenance, template-rendered memory, and the calibrated greedy-reference outcome. The evaluator loads the complete file but constructs restricted observations for the policy. These published development scenarios are not a hidden test set.

The `v1` directory name is a dataset label, not a package version. The benchmark schema is still `0.1.0`. The five development files and all ten embedded v15 scenarios were checked for exact agreement on September 9, 2026. The full v1 set has not been evaluated by both models in v15; only its five-scenario subset has.

Generate new scenarios into a separate directory, preserving the reviewed snapshots:

```sh
uv run execbench generate --out scenarios/generated-review --count 50 --seed 1000
```

This uses deterministic memory templates and needs no API key. Simulation or generation changes can change the files and stored reference outcomes even when the seeds are unchanged.
