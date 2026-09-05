# ExecBench leaderboard

Metric means; no composite score. Missing LLM grades are shown as —. Zero latency with zero detection does not mean fast detection. Oracle is a greedy reference, not a proven upper bound.

## Difficulty all

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 50 | 0 | 0.372 | 0.628 | 0.000 | 0.543 | 0.000 | 0.013 | — | 0.000 | 0.000 | 0.740 | 0.000 | 0.993 | 0.000 | 0.000 |
| heuristic | 50 | 0 | 0.563 | 0.437 | 0.815 | 0.613 | 0.000 | -0.141 | — | 0.000 | 0.000 | 0.450 | 0.010 | 0.991 | 0.000 | 0.000 |
| oracle | 50 | 0 | 1.000 | 0.000 | 1.000 | 0.020 | 0.020 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.280 | 0.704 | 0.000 | 0.000 |
| random | 50 | 0 | 0.002 | 0.998 | 0.776 | 0.160 | 0.030 | 0.068 | 0.000 [19/50] | 0.000 [49/50] | 0.000 [49/50] | 0.330 | 0.180 | 0.250 | 0.000 | 0.000 |
| trust_all | 50 | 0 | 0.546 | 0.454 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.280 | 0.602 | 0.000 | 0.000 |

## Difficulty 1

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 0 | 0.316 | 0.684 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.300 | 0.000 | 0.992 | 0.000 | 0.000 |
| heuristic | 10 | 0 | 0.562 | 0.438 | 1.000 | 0.000 | 0.000 | 0.013 | — | 0.000 | 0.000 | 0.150 | 0.050 | 0.984 | 0.000 | 0.000 |
| oracle | 10 | 0 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.100 | 0.636 | 0.000 | 0.000 |
| random | 10 | 0 | 0.000 | 1.000 | 0.700 | 0.000 | 0.000 | 0.100 | 0.000 [3/10] | 0.000 | 0.000 | 0.200 | 0.100 | 0.254 | 0.000 | 0.000 |
| trust_all | 10 | 0 | 0.748 | 0.252 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.100 | 0.570 | 0.000 | 0.000 |

## Difficulty 2

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 0 | 0.380 | 0.620 | 0.000 | 0.700 | 0.000 | 0.087 | — | 0.000 | 0.000 | 0.900 | 0.000 | 0.993 | 0.000 | 0.000 |
| heuristic | 10 | 0 | 0.554 | 0.446 | 0.667 | 0.700 | 0.000 | -0.287 | — | 0.000 | 0.000 | 0.400 | 0.000 | 0.993 | 0.000 | 0.000 |
| oracle | 10 | 0 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.400 | 0.667 | 0.000 | 0.000 |
| random | 10 | 0 | -0.013 | 1.013 | 0.733 | 0.100 | 0.000 | -0.323 | 0.000 [5/10] | 0.000 | 0.000 | 0.450 | 0.100 | 0.232 | 0.000 | 0.000 |
| trust_all | 10 | 0 | 0.594 | 0.406 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.400 | 0.597 | 0.000 | 0.000 |

## Difficulty 3

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 0 | 0.396 | 0.604 | 0.000 | 0.450 | 0.000 | 0.054 | — | 0.000 | 0.000 | 0.800 | 0.000 | 0.995 | 0.000 | 0.000 |
| heuristic | 10 | 0 | 0.615 | 0.385 | 0.800 | 0.800 | 0.000 | -0.180 | — | 0.000 | 0.000 | 0.650 | 0.000 | 0.993 | 0.000 | 0.000 |
| oracle | 10 | 0 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.400 | 0.700 | 0.000 | 0.000 |
| random | 10 | 0 | 0.003 | 0.997 | 0.897 | 0.200 | 0.000 | 0.102 | 0.000 [3/10] | 0.000 [9/10] | 0.000 [9/10] | 0.350 | 0.300 | 0.345 | 0.000 | 0.000 |
| trust_all | 10 | 0 | 0.534 | 0.466 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.400 | 0.618 | 0.000 | 0.000 |

## Difficulty 4

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 0 | 0.352 | 0.648 | 0.000 | 0.700 | 0.000 | -0.045 | — | 0.000 | 0.000 | 0.900 | 0.000 | 0.992 | 0.000 | 0.000 |
| heuristic | 10 | 0 | 0.551 | 0.449 | 0.857 | 0.750 | 0.000 | -0.138 | — | 0.000 | 0.000 | 0.450 | 0.000 | 0.992 | 0.000 | 0.000 |
| oracle | 10 | 0 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.100 | 0.737 | 0.000 | 0.000 |
| random | 10 | 0 | 0.019 | 0.981 | 0.752 | 0.300 | 0.150 | 0.265 | 0.000 [4/10] | 0.000 | 0.000 | 0.400 | 0.100 | 0.273 | 0.000 | 0.000 |
| trust_all | 10 | 0 | 0.426 | 0.574 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.100 | 0.580 | 0.000 | 0.000 |

## Difficulty 5

| Policy | Episodes | Failed | outcome | regret | escalation_f1 | detection_rate | mean_detection_latency | verification_calibration | report_honesty | coaching_score | coaching_false_positive_rate | prior_utilization | stale_trust | compute_fraction | llm_cost_usd | parse_forced_wait_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audit_all | 10 | 0 | 0.416 | 0.584 | 0.000 | 0.867 | 0.000 | -0.034 | — | 0.000 | 0.000 | 0.800 | 0.000 | 0.993 | 0.000 | 0.000 |
| heuristic | 10 | 0 | 0.535 | 0.465 | 0.750 | 0.817 | 0.000 | -0.116 | — | 0.000 | 0.000 | 0.600 | 0.000 | 0.994 | 0.000 | 0.000 |
| oracle | 10 | 0 | 1.000 | 0.000 | 1.000 | 0.100 | 0.100 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.400 | 0.778 | 0.000 | 0.000 |
| random | 10 | 0 | 0.000 | 1.000 | 0.800 | 0.200 | 0.000 | 0.198 | 0.000 [4/10] | 0.000 | 0.000 | 0.250 | 0.300 | 0.147 | 0.000 | 0.000 |
| trust_all | 10 | 0 | 0.426 | 0.574 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.400 | 0.642 | 0.000 | 0.000 |
