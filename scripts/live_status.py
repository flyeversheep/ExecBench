"""Compact status for a running benchmark, without reading credentials or full traces."""

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="?", default="results/live-demo-resumed")
    args = parser.parse_args()
    root = Path(args.results)
    rows_path = root / "scores.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()] if rows_path.exists() else []
    counts = Counter((r["policy"], r["status"]) for r in rows)
    print(
        json.dumps(
            {
                "completed": sum(r["status"] == "ok" for r in rows),
                "policies": {
                    p: {"ok": counts[p, "ok"], "error": counts[p, "error"]}
                    for p in sorted({r["policy"] for r in rows})
                },
                "errors": [
                    {"scenario": r["scenario_id"], "policy": r["policy"], "error": r["error"]}
                    for r in rows
                    if r["status"] == "error"
                ][:5],
                "forced_wait_episodes": sum(
                    r["scores"].get("parse_forced_wait_rate", 0) > 0 for r in rows if r["status"] == "ok"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
