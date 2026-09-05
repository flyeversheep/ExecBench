"""Preflight the configured account before dispatching a resumable live demo."""

import argparse
import subprocess
import sys
from pathlib import Path

from execbench.llm.client import LLMClient
from execbench.runner.leaderboard import leaderboard
from execbench.runner.run_benchmark import run_benchmark


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="glm-5.1,glm-5,glm-4.7")
    parser.add_argument("--grader-model", default="glm-4.7")
    parser.add_argument("--scenario-set", default="scenarios/v0")
    parser.add_argument("--out", default="results/live-demo")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    models = args.models.split(",")
    for model in dict.fromkeys([*models, args.grader_model]):
        LLMClient(model).complete(
            [{"role": "user", "content": "Reply with the single word OK."}], max_tokens=32
        )
        print(f"API preflight succeeded: {model}", flush=True)
    subprocess.run(
        [
            sys.executable,
            "scripts/validate_live_graders.py",
            "--model",
            args.grader_model,
            "--out",
            str(Path(args.out) / "grader-validation.json"),
        ],
        check=True,
    )
    rows = run_benchmark(
        args.scenario_set,
        ["oracle", "heuristic", "trust_all", "audit_all", *models],
        args.out,
        args.workers,
        args.grader_model,
    )
    leaderboard(args.out)
    failed = [r for r in rows if r["status"] != "ok"]
    print(f"{len(rows) - len(failed)} completed; {len(failed)} failed. Results: {args.out}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
