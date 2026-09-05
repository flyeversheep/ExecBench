# ExecBench live run report — September 5, 2026

The resumed run stopped because Z.ai returned HTTP 429 with error code **1113: insufficient balance**. The process exited with status 1 and saved `blocked_account_balance`. No new API calls or restart were made to prepare this report.

**208 of 350 planned episodes completed (59.4%)**: 76 executive-model episodes and 132 live-graded scripted episodes. There are 23 failed episode records (16 balance errors and 7 transport read timeouts), plus 119 planned episodes without a saved result. Thus 142 episodes remain incomplete. Failures are excluded from score averages, not scored as poor policy decisions. Cached calls from the earlier run were reused; its completed episodes must not be added to this run's counts.

| Policy | Completed / 50 | Balance errors | Timeouts | No saved result |
|---|---:|---:|---:|---:|
| glm-5 | 31 | 2 | 0 | 17 |
| glm-5.1 | 30 | 3 | 0 | 17 |
| glm-4.7 | 15 | 11 | 7 | 17 |
| heuristic | 33 | 0 | 0 | 17 |
| trust_all | 33 | 0 | 0 | 17 |
| audit_all | 33 | 0 | 0 | 17 |
| oracle | 33 | 0 | 0 | 17 |

GLM-5 and GLM-5.1 completed all 30 difficulty 1–3 scenarios. GLM-5 additionally completed one difficulty-4 scenario. GLM-4.7 completed nine difficulty-1, five difficulty-2, and one difficulty-3 scenario. Each scripted policy completed 33 scenarios. No difficulty-5 results completed. GLM-4.7 accounts for all seven transport timeouts; this is infrastructure evidence, not evidence of weaker management behavior.

## Comparisons on the same scenarios

Outcome is completed quality minus penalties, normalized to the same-scenario greedy oracle. The oracle is an empirical reference, not a proven upper bound. These are descriptive means from single cached runs, not statistical claims or a complete five-level ranking. Detection means include zero where no misleading worker was eligible; escalation F1 uses 1 when there was no escalation opportunity.

### All seven policies: 15 shared scenarios (9 at difficulty 1, 5 at difficulty 2, 1 at difficulty 3)

| Policy | Outcome | Escalation F1 | Detection rate | Compute used |
|---|---:|---:|---:|---:|
| glm-5 | 0.894 | 0.876 | 0.267 | 88.2% |
| glm-5.1 | 0.816 | 0.876 | 0.100 | 69.7% |
| glm-4.7 | 0.793 | 0.667 | 0.133 | 62.9% |
| heuristic | 0.578 | 0.876 | 0.267 | 98.8% |
| trust_all | 0.706 | 0.000 | 0.000 | 58.2% |
| audit_all | 0.387 | 0.000 | 0.267 | 99.2% |
| oracle | 1.000 | 1.000 | 0.000 | 65.1% |

### GLM-5 versus GLM-5.1 and baselines: 30 shared scenarios (10 each at difficulties 1–3)

| Policy | Outcome | Escalation F1 | Detection rate | Compute used |
|---|---:|---:|---:|---:|
| glm-5 | 0.864 | 0.822 | 0.383 | 85.9% |
| glm-5.1 | 0.774 | 0.822 | 0.183 | 74.6% |
| heuristic | 0.577 | 0.822 | 0.500 | 99.0% |
| trust_all | 0.625 | 0.000 | 0.000 | 59.5% |
| audit_all | 0.364 | 0.000 | 0.383 | 99.3% |
| oracle | 1.000 | 1.000 | 0.000 | 66.8% |

On the 30 shared scenarios, GLM-5 achieved higher outcome than GLM-5.1 (0.864 versus 0.774), with equal mean escalation F1 and higher detection, while consuming more simulated compute (85.9% versus 74.6%). The heuristic detected more misleading behavior on average but produced lower outcome. AuditAll consumed almost all compute and had the lowest outcome in this comparison. These patterns describe these seeds and policies; they do not establish causal effects.

All 76 completed model episodes had **zero parse-failure forced waits across 2,652 actions**. This does not imply every model response was valid on its first attempt, nor does it cover incomplete episodes.

## API cost estimate

The local cache contains 3,268 unique successful responses across both attempts, validation, grading, and unfinished episodes. At the rates used for this run:

| API model (all roles) | Responses | Input tokens | Output tokens | Cache-adjusted estimate | Full input price estimate |
|---|---:|---:|---:|---:|---:|
| glm-5 | 1,026 | 16,632,053 | 220,992 | $11.78 | $17.34 |
| glm-5.1 | 1,412 | 27,525,407 | 120,744 | $29.16 | $39.07 |
| glm-4.7 | 830 | 8,240,951 | 111,647 | $2.85 | $5.19 |

**Cumulative estimated cost: $43.79 with reported provider-cache discounts; $61.60 at full input prices.** This is not an invoice or the amount spent since the latest recharge. Interrupted or duplicate in-flight calls may be missing; repeated local cache replays are counted once. GLM-4.7 includes grading for every policy as well as its own executive calls. Trace costs exclude local cache hits and use full input rates, so they measure a different scope and should not be summed with this ledger.

Rates in USD per million input / cached input / output tokens: GLM-5.1 1.40 / 0.26 / 4.40; GLM-5 1.00 / 0.20 / 3.20; GLM-4.7 0.60 / 0.11 / 2.20. These are the pricing assumptions recorded for this evaluation, previously checked against [Z.ai pricing](https://docs.z.ai/guides/overview/pricing). No billing-account balance was queried for this report; depletion is confirmed by saved provider errors.

## Grading limitations

All five synthetic live grader acceptance checks passed. Nevertheless, actual narrative spot-checks found missing truth context for budgets, time and worker identities; medium-quality tasks sometimes counted as material omissions; and overlapping task/project requirement omissions. **Treat report-honesty scores as exploratory and unsuitable for a firm model ranking.** The frozen grader was preserved throughout. See [grading notes](GRADING_NOTES.md). Coaching is also model-graded; outcome, escalation, detection, and resource accounting are deterministic.

## Remaining work and evidence

Completing the planned run requires retrying 23 failed episodes and running the 119 without saved results after API credit is available. Preserve the response cache and manifest; use fewer workers when retrying transport failures. No reliable remaining-dollar estimate follows from these partial results: later scenarios and cached partial episodes have different costs. A future budget cap would help prevent another uncontrolled depletion. Any rubric correction should be a separately versioned evaluation.

- [Full partial leaderboard](leaderboard.md), including per-difficulty means with unequal coverage.
- [Matched comparison data](matched-comparisons.json) and [episode score records](scores.jsonl).
- [Coverage and usage](summary.json), [terminal run status](run_status.json), [cost ledger](cost-ledger.json), and [run manifest](manifest.json).
- [Live acceptance evidence](grader-validation.json).
- Offline interactive traces: [GLM-5](glm-5.html), [GLM-5.1](glm-5.1.html), [GLM-4.7](glm-4.7.html).

This report is a final snapshot of an incomplete run. The benchmark remains stopped.
