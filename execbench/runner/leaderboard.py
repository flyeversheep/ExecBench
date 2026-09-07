import json
import statistics
from collections import defaultdict
from pathlib import Path

PROFILE = [
    "outcome",
    "regret",
    "escalation_f1",
    "detection_rate",
    "mean_detection_latency",
    "verification_calibration",
    "report_honesty",
    "coaching_score",
    "coaching_false_positive_rate",
    "prior_utilization",
    "stale_trust",
    "compute_fraction",
    "specification_precision",
    "llm_cost_usd",
    "parse_forced_wait_rate",
]


def leaderboard(result_dir):
    root = Path(result_dir)
    rows = [json.loads(line) for line in (root / "scores.jsonl").read_text().splitlines()]
    groups = defaultdict(list)
    for row in rows:
        for level in ("all", str(row["level"])):
            groups[(level, row["policy"])].append(row)
    output = []
    for (level, policy), data in sorted(groups.items()):
        ok = [r for r in data if r["status"] == "ok"]
        means, counts = {}, {}
        for metric in PROFILE:
            vals = [
                r["scores"][metric]
                for r in ok
                if metric in r["scores"]
                and (metric != "llm_cost_usd" or r["scores"].get("llm_cost_known", 0))
            ]
            if vals:
                means[metric], counts[metric] = statistics.mean(vals), len(vals)
        output.append(
            {
                "level": level,
                "policy": policy,
                "episodes": len(ok),
                "failures": len(data) - len(ok),
                "metrics": means,
                "metric_sample_counts": counts,
            }
        )
    (root / "leaderboard.json").write_text(json.dumps(output, indent=2) + "\n")
    lines = [
        "# ExecBench leaderboard",
        "",
        "Metric means; no composite score. Missing LLM grades are shown as —. "
        "Zero latency with zero detection does not mean fast detection. Oracle is a greedy reference, not a proven upper bound.",
        "",
    ]
    for level in ["all", "1", "2", "3", "4", "5"]:
        selected = [r for r in output if r["level"] == level]
        if not selected:
            continue
        lines += [
            f"## Difficulty {level}",
            "",
            "| Policy | Episodes | Failed | " + " | ".join(PROFILE) + " |",
            "|---|---:|---:|" + "---:|" * len(PROFILE),
        ]
        for row in selected:
            vals = []
            for m in PROFILE:
                if m not in row["metrics"]:
                    vals.append("—")
                else:
                    value = f"{row['metrics'][m]:.3f}"
                    if row["metric_sample_counts"][m] < row["episodes"]:
                        value += f" [{row['metric_sample_counts'][m]}/{row['episodes']}]"
                    vals.append(value)
            lines.append(
                f"| {row['policy']} | {row['episodes']} | {row['failures']} | " + " | ".join(vals) + " |"
            )
        lines.append("")
    (root / "leaderboard.md").write_text("\n".join(lines))
    return output
