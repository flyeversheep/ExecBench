"""Build reviewable evidence from completed live benchmark runs."""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from execbench.runner.leaderboard import leaderboard
from execbench.runner.run_episode import read_trace
from execbench.viewer.trace_viewer import render_trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/live-demo")
    parser.add_argument("--out", default="demo/live")
    args = parser.parse_args()
    root, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    board = leaderboard(root)
    rows = [json.loads(x) for x in (root / "scores.jsonl").read_text().splitlines()]
    for name in [
        "scores.jsonl",
        "leaderboard.json",
        "leaderboard.md",
        "manifest.json",
        "grader-validation.json",
    ]:
        if (root / name).exists():
            shutil.copyfile(root / name, out / name)
    summaries = []
    for entry in board:
        if entry["level"] != "all":
            continue
        selected = [r for r in rows if r["policy"] == entry["policy"] and r["status"] == "ok"]
        totals = Counter()
        cost, grader_cost = 0.0, 0.0
        for row in selected:
            trace = read_trace(root / row["trace"])
            actions = [s for s in trace.steps if s.action]
            totals["actions"] += len(actions)
            totals["forced_waits"] += sum(
                "three invalid model responses; forced wait" in s.observation.errors for s in actions
            )
            totals["input_tokens"] += trace.scores["llm_input_tokens"]
            totals["output_tokens"] += trace.scores["llm_output_tokens"]
            cost += trace.scores["llm_cost_usd"]
            grader_cost += trace.scores.get("grader_cost_usd", 0)
        summaries.append(
            {
                **entry,
                "usage": dict(totals),
                "policy_cost_estimate_usd": cost,
                "grader_cost_estimate_usd": grader_cost,
                "weighted_forced_wait_rate": totals["forced_waits"] / max(totals["actions"], 1),
            }
        )
        if entry["policy"].startswith("glm-") and selected:
            # Prefer an episode with both observed misleadingness and a management response.
            row = max(
                selected,
                key=lambda r: (
                    r["scores"].get("misleading_ic_count", 0) > 0,
                    r["scores"].get("detection_rate", 0),
                    r["scores"].get("outcome", 0),
                ),
            )
            source = root / row["trace"]
            shutil.copyfile(source, out / source.name)
            render_trace(source, out / (entry["policy"] + ".html"))
    (out / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(
        json.dumps(
            [
                {
                    k: s[k]
                    for k in [
                        "policy",
                        "episodes",
                        "failures",
                        "weighted_forced_wait_rate",
                        "policy_cost_estimate_usd",
                        "grader_cost_estimate_usd",
                    ]
                }
                for s in summaries
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
