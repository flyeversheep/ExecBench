import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from execbench.llm.client import LLMBalanceError, LLMClient
from execbench.runner.run_episode import read_scenario, run_episode, write_trace


def slug(value):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)


def implementation_hash():
    package = Path(__file__).resolve().parents[1]
    code_hash = hashlib.sha256()
    for source in sorted(p for p in package.rglob("*") if p.suffix in (".py", ".md", ".yaml")):
        code_hash.update(str(source.relative_to(package)).encode())
        code_hash.update(source.read_bytes())
    return code_hash.hexdigest()


def run_benchmark(scenario_set, policies, out, workers=8, grader_model=None, resume=True):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scenarios = sorted(Path(scenario_set).glob("*.json"))
    if not scenarios:
        raise ValueError("scenario set contains no JSON scenarios")
    manifest = {
        "implementation_sha256": implementation_hash(),
        "history_chars": int(os.getenv("EXECBENCH_HISTORY_CHARS", "60000")),
        "provider": os.getenv("EXECBENCH_PROVIDER", "openai"),
        "base_url": os.getenv("EXECBENCH_BASE_URL", "default"),
        "pricing": json.loads(os.getenv("EXECBENCH_PRICES_JSON", "{}")),
        "version": "0.1.0",
        "policies": policies,
        "grader_model": grader_model,
        "scenarios": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in scenarios},
    }
    manifest_path = out / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise ValueError("result directory belongs to a different run configuration; choose a new --out")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    path = out / "scores.jsonl"
    rows = [json.loads(x) for x in path.read_text().splitlines()] if resume and path.exists() else []
    complete = {(x["scenario_id"], x["policy"]) for x in rows if x.get("status") == "ok"}
    rows = [r for r in rows if r.get("status") == "ok"]

    def job(scenario_path, policy):
        scenario = read_scenario(scenario_path)
        try:
            trace = run_episode(
                scenario, policy, grader_client=LLMClient(grader_model) if grader_model else None
            )
            trace_path = out / "traces" / f"{scenario.scenario_id}__{slug(policy)}.json.gz"
            write_trace(trace, trace_path)
            return {
                "scenario_id": scenario.scenario_id,
                "policy": policy,
                "level": scenario.difficulty.level,
                "status": "ok",
                "scores": trace.scores,
                "grading_mode": trace.grading["mode"],
                "trace": str(trace_path.relative_to(out)),
            }
        except Exception as exc:
            return {
                "scenario_id": scenario.scenario_id,
                "policy": policy,
                "level": scenario.difficulty.level,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "error_kind": "account_balance" if isinstance(exc, LLMBalanceError) else "episode_error",
            }

    blocked = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(job, s, p)
            for s in scenarios
            for p in policies
            if (read_scenario(s).scenario_id, p) not in complete
        ]
        for future in as_completed(futures):
            if future.cancelled():
                continue
            row = future.result()
            rows.append(row)
            if row.get("error_kind") == "account_balance":
                blocked = True
                # Cancel queued episodes; retain results from the few already running.
                for pending in futures:
                    pending.cancel()
            temp = out / "scores.tmp"
            temp.write_text(
                "".join(
                    json.dumps(r, sort_keys=True) + "\n"
                    for r in sorted(rows, key=lambda r: (r["scenario_id"], r["policy"]))
                )
            )
            temp.replace(path)
    (out / "run_status.json").write_text(
        json.dumps(
            {
                "status": "blocked_account_balance" if blocked else "finished",
                "planned_episodes": len(scenarios) * len(policies),
                "completed_episodes": sum(r["status"] == "ok" for r in rows),
                "failed_attempts": sum(r["status"] == "error" for r in rows),
            },
            indent=2,
        )
        + "\n"
    )
    return sorted(rows, key=lambda r: (r["scenario_id"], r["policy"]))
