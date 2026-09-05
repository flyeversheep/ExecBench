"""Rebuild the local baseline demo and its reviewable, checked-in evidence."""

import shutil
from pathlib import Path

from execbench.runner.leaderboard import leaderboard
from execbench.runner.run_benchmark import implementation_hash, run_benchmark
from execbench.runner.run_episode import read_scenario, run_episode, write_trace
from execbench.viewer.trace_viewer import render_trace


def main():
    root = Path("demo")
    root.mkdir(exist_ok=True)
    results = Path("results") / ("demo-" + implementation_hash()[:12])
    rows = run_benchmark("scenarios/v0", ["oracle", "heuristic", "trust_all", "audit_all", "random"], results)
    leaderboard(results)
    for name in ["scores.jsonl", "leaderboard.json", "leaderboard.md", "manifest.json"]:
        shutil.copyfile(results / name, root / name)
    for scenario_id, policy, name in [
        ("l2_01010", "trust_all", "stale-trust"),
        ("l2_01010", "heuristic", "verification"),
        ("l2_01010", "audit_all", "audit-cost"),
    ]:
        path = next(Path("scenarios/v0").glob(f"{scenario_id}.json"))
        trace = run_episode(read_scenario(path), policy)
        write_trace(trace, root / f"{name}.json.gz")
        render_trace(trace, root / f"{name}.html")
    print(f"Built {len(rows)} baseline episodes and three trace viewers in {root.resolve()}")


if __name__ == "__main__":
    main()
