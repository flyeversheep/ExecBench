# ExecBench leaderboard

Metric means; no composite score. Missing LLM grades are shown as —. Zero latency with zero detection does not mean fast detection. Oracle is a greedy reference, not a proven upper bound.

## Difficulty all

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 12 | 0.316 | 0.684 | 0.000 | 0.000 | 0.000 | 0.000 | 0.925 | 0.000 | 0.000 | 0.300 | 0.000 | 0.992 | 0.000 | 0.000 |
| glm-4.7 | 1 | 20 | 0.813 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 0.136 | 0.000 | 0.000 | 0.000 | 0.000 | 0.592 | 0.110 | 0.000 |
| glm-5 | 5 | 16 | 0.844 | 0.156 | 1.000 | 0.000 | 0.000 | 0.000 | 0.305 | 0.000 | 0.000 | 0.100 | 0.100 | 0.915 | 0.314 | 0.000 |
| glm-5.1 | 4 | 18 | 0.777 | 0.223 | 1.000 | 0.000 | 0.000 | -0.433 | 0.388 | 0.000 | 0.000 | 0.000 | 0.000 | 0.659 | 0.415 | 0.000 |
| heuristic | 10 | 12 | 0.562 | 0.438 | 1.000 | 0.000 | 0.000 | 0.013 | 1.000 | 0.000 | 0.000 | 0.150 | 0.050 | 0.984 | 0.000 | 0.000 |
| oracle | 10 | 12 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.100 | 0.636 | 0.000 | 0.000 |
| trust_all | 10 | 12 | 0.748 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 0.740 | 0.000 | 0.000 | 0.000 | 0.100 | 0.570 | 0.000 | 0.000 |

## Difficulty 1

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 0 | 0.316 | 0.684 | 0.000 | 0.000 | 0.000 | 0.000 | 0.925 | 0.000 | 0.000 | 0.300 | 0.000 | 0.992 | 0.000 | 0.000 |
| glm-4.7 | 1 | 9 | 0.813 | 0.187 | 0.000 | 0.000 | 0.000 | 0.000 | 0.136 | 0.000 | 0.000 | 0.000 | 0.000 | 0.592 | 0.110 | 0.000 |
| glm-5 | 5 | 5 | 0.844 | 0.156 | 1.000 | 0.000 | 0.000 | 0.000 | 0.305 | 0.000 | 0.000 | 0.100 | 0.100 | 0.915 | 0.314 | 0.000 |
| glm-5.1 | 4 | 6 | 0.777 | 0.223 | 1.000 | 0.000 | 0.000 | -0.433 | 0.388 | 0.000 | 0.000 | 0.000 | 0.000 | 0.659 | 0.415 | 0.000 |
| heuristic | 10 | 0 | 0.562 | 0.438 | 1.000 | 0.000 | 0.000 | 0.013 | 1.000 | 0.000 | 0.000 | 0.150 | 0.050 | 0.984 | 0.000 | 0.000 |
| oracle | 10 | 0 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.100 | 0.636 | 0.000 | 0.000 |
| trust_all | 10 | 0 | 0.748 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | 0.740 | 0.000 | 0.000 | 0.000 | 0.100 | 0.570 | 0.000 | 0.000 |

## Difficulty 2

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| glm-4.7 | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| glm-5 | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| glm-5.1 | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| heuristic | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| oracle | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| trust_all | 0 | 10 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## Difficulty 3

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 0 | 2 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| glm-4.7 | 0 | 1 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| glm-5 | 0 | 1 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| glm-5.1 | 0 | 2 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| heuristic | 0 | 2 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| oracle | 0 | 2 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| trust_all | 0 | 2 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
