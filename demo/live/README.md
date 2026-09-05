# Partial live run — blocked by API balance

The credential succeeded on 2026-09-05. API preflights passed for GLM-5.1, GLM-5, and GLM-4.7, and **all five live grader acceptance checks passed**. The benchmark stopped when the general Z.ai API returned HTTP 429 with provider error **1113: insufficient balance or no resource package**.

| Policy | Completed scenarios / planned |
|---|---:|
| GLM-5 | 5 / 50 |
| GLM-5.1 | 4 / 50 |
| GLM-4.7 | 1 / 50 |
| Oracle, Heuristic, TrustAll, AuditAll | 10 / 50 each |

All completed model episodes had zero parse-failure forced waits (248 actions total). Live-graded oracle reports averaged 1.0 honesty across ten episodes. These are early, unequal scenario subsets, so their average scores must not be read as a model ranking. The “Failed” column in the provisional leaderboard counts provider-error attempts, not poor policy behavior. Most planned episodes remain incomplete or unattempted.

- [Provisional leaderboard](leaderboard.md) and [coverage/usage summary](summary.json)
- [Live grader acceptance evidence](grader-validation.json)
- [GLM-5.1 trace](glm-5.1.html), [GLM-5 trace](glm-5.html), [GLM-4.7 trace](glm-4.7.html)
- [Cost ledger](cost-ledger.json): approximately **$6.24 at full input/output list prices** for unique cached responses, including unfinished episodes and grader/preflight calls. This is not an invoice: provider cache discounts are excluded, and interrupted or duplicate in-flight requests may not be captured. Completed-trace cost totals alone undercount calls made before interruption.

Prices were checked against [Z.ai’s official pricing](https://docs.z.ai/guides/overview/pricing). All requests and raw model responses remain in the local `.cache/llm` directory; credentials are not stored there. Full original traces are under `results/live-demo/traces` from the repository root.

The live run exposed and fixed two integration issues: the grader sometimes emits an out-of-range arithmetic summary despite valid claim judgments (the benchmark now accepts that informational field and still computes its own bounded score), and Z.ai uses HTTP 429 for an empty balance (the runner now detects code 1113 and cancels queued work).

After adding API credit, resume from the repository root:

```sh
export EXECBENCH_API_KEY_REF='op://AI agents/Z.ai API/credential'
export EXECBENCH_PRICES_JSON='{"glm-5.1":{"input":1.4,"output":4.4},"glm-5":{"input":1.0,"output":3.2},"glm-4.7":{"input":0.6,"output":2.2}}'
uv run python scripts/run_live_demo.py --workers 6 --out results/live-demo-resumed
uv run python scripts/summarize_live.py --results results/live-demo-resumed --out demo/live-complete
```

The new result directory preserves the original run’s manifest while allowing the balance-handling implementation fix. Prior model responses are replayed from the same cache. The benchmark will not silently mix implementation hashes.
