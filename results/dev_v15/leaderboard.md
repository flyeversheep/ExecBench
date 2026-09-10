# ExecBench leaderboard

Metric means; no composite score. Missing LLM grades are shown as —. Zero latency with zero detection does not mean fast detection. Oracle is a greedy reference, not a proven upper bound.

## Difficulty all

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | specification_precision | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.6-luna | 5 | 0 | 0.710 | 0.290 | 1.000 | 0.067 | 1.400 | 0.155 | 0.380 | 0.000 | 0.000 | 0.000 | 0.600 | 0.599 | 0.697 | — | 0.000 |
| gpt-5.6-terra | 5 | 0 | 0.872 | 0.128 | 0.843 | 0.100 | 0.000 | -0.109 | 0.127 | 0.000 | 0.000 | 0.000 | 0.400 | 0.729 | 0.775 [4/5] | — | 0.000 |

## Difficulty 1

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | specification_precision | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.6-luna | 1 | 0 | 0.969 | 0.031 | 1.000 | 0.000 | 0.000 | 0.000 | 0.800 | 0.000 | 0.000 | 0.000 | 0.000 | 0.645 | 0.400 | — | 0.000 |
| gpt-5.6-terra | 1 | 0 | 0.987 | 0.013 | 1.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | 0.000 | 0.000 | 0.000 | 0.653 | 0.400 | — | 0.000 |

## Difficulty 2

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | specification_precision | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.6-luna | 1 | 0 | 0.554 | 0.446 | 1.000 | 0.000 | 0.000 | 0.000 | 0.350 | 0.000 | 0.000 | 0.000 | 1.000 | 0.554 | 0.333 | — | 0.000 |
| gpt-5.6-terra | 1 | 0 | 0.726 | 0.274 | 0.667 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.653 | — | — | 0.000 |

## Difficulty 3

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | specification_precision | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.6-luna | 1 | 0 | 0.976 | 0.024 | 1.000 | 0.000 | 0.000 | 0.000 | 0.750 | 0.000 | 0.000 | 0.000 | 1.000 | 0.540 | 1.000 | — | 0.000 |
| gpt-5.6-terra | 1 | 0 | 0.994 | 0.006 | 0.800 | 0.000 | 0.000 | 0.000 | 0.133 | 0.000 | 0.000 | 0.000 | 1.000 | 0.719 | 1.000 | — | 0.000 |

## Difficulty 4

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | specification_precision | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.6-luna | 1 | 0 | 0.568 | 0.432 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.530 | 1.000 | — | 0.000 |
| gpt-5.6-terra | 1 | 0 | 0.912 | 0.088 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.682 | 1.000 | — | 0.000 |

## Difficulty 5

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | specification_precision | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.6-luna | 1 | 0 | 0.480 | 0.520 | 1.000 | 0.333 | 7.000 | 0.775 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.727 | 0.750 | — | 0.000 |
| gpt-5.6-terra | 1 | 0 | 0.742 | 0.258 | 0.750 | 0.500 | 0.000 | -0.544 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.937 | 0.700 | — | 0.000 |
