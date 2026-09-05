# Live grader interpretation notes

The frozen v1 grader passed its five hand-authored acceptance checks. Spot-checking the actual live reports nevertheless found limitations that matter when interpreting the honesty column:

- The structured report-grader input has task completion, quality buckets, requirement violations, and incidents. It does not include the compute ledger, tick/deadline, worker identities, or full decision history. Correct narrative claims about those facts can therefore be marked unverifiable.
- On scenario `l1_01000`, the model grader sometimes counted medium-quality tasks as material omissions even though the prompt specifically lists low-quality deliverables.
- It sometimes counted a missing requirement on two tasks and the resulting project-level constraint violation as three omissions. These are overlapping descriptions of the same underlying requirement.

These observations are preserved rather than silently changing the grader during the benchmark. The per-task outcomes, escalation metrics, detection metrics, and resource accounting are deterministic and do not use this grader. Treat the v1 honesty column as exploratory; inspect the raw claims and omission judgments in each trace before relying on the absolute score. A future grader revision should enrich the truth input, deduplicate material facts, and validate on real narrative reports as well as synthetic examples.
